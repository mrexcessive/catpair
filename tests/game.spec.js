// @ts-check
const { test, expect } = require('@playwright/test');

const BASE_URL = 'http://localhost:8765';

test.describe('CatPair Mahjong Game', () => {

  test.beforeEach(async ({ page }) => {
    await page.goto(BASE_URL);
    // Wait for tiles to load
    await page.waitForSelector('.tile', { timeout: 10000 });
    // Small extra wait for rendering
    await page.waitForTimeout(300);
  });

  test('default 10x10 stacked: renders tiles across multiple layers', async ({ page }) => {
    const tileCount = await page.locator('.tile').count();
    // 10x10 stacked = 426 tiles
    expect(tileCount).toBe(426);

    // Score bar shows correct total pairs
    const totalPairs = await page.locator('#total-pairs').textContent();
    expect(totalPairs).toBe('213');
  });

  test('settings buttons are present and functional', async ({ page }) => {
    // Grid buttons
    await expect(page.locator('button[data-value="6"]')).toBeVisible();
    await expect(page.locator('button[data-value="8"]')).toBeVisible();
    await expect(page.locator('button[data-value="10"]')).toBeVisible();

    // Depth buttons
    await expect(page.locator('button[data-value="flat"]')).toBeVisible();
    await expect(page.locator('button[data-value="stacked"]')).toBeVisible();

    // 10x10 and stacked should be active by default
    await expect(page.locator('button[data-value="10"]')).toHaveClass(/active/);
    await expect(page.locator('button[data-value="stacked"]')).toHaveClass(/active/);
  });

  test('tiles have absolute positioning with z-index for layers', async ({ page }) => {
    // Check that tiles use absolute positioning
    const position = await page.locator('.tile').first().evaluate(el => {
      return window.getComputedStyle(el).position;
    });
    expect(position).toBe('absolute');

    // Check there are tiles at different z-index levels
    const zIndices = await page.locator('.tile').evaluateAll(els => {
      const indices = new Set(els.map(el => parseInt(window.getComputedStyle(el).zIndex) || 0));
      return Array.from(indices).sort((a, b) => a - b);
    });
    // Should have tiles at z=0, z=1, z=2, z=3, z=4 (×100 base)
    expect(zIndices.length).toBeGreaterThan(1);
  });

  test('blocked tiles have blocked class and exposed tiles do not', async ({ page }) => {
    const blockedCount = await page.locator('.tile.blocked').count();
    const totalCount = await page.locator('.tile').count();

    // In stacked mode, most tiles should be blocked (only top layer + some exposed)
    expect(blockedCount).toBeGreaterThan(0);
    expect(blockedCount).toBeLessThan(totalCount);
  });

  test('clicking a blocked tile does nothing', async ({ page }) => {
    // Find a blocked tile and try to click it
    const blockedTile = page.locator('.tile.blocked').first();
    if (await blockedTile.count() > 0) {
      await blockedTile.click({ force: true });
      // No tile should become selected (pointer-events: none should prevent it,
      // but with force:true we bypass that — the JS handler should still reject it)
      // Check that match count is still 0
      const matchCount = await page.locator('#match-count').textContent();
      expect(matchCount).toBe('0');
    }
  });

  test('can match two exposed tiles with same image', async ({ page }) => {
    // Get all exposed (non-blocked) tiles
    const exposedTiles = page.locator('.tile:not(.blocked):not(.matched)');
    const count = await exposedTiles.count();
    expect(count).toBeGreaterThanOrEqual(2);

    // Find a matching pair among exposed tiles
    const tileData = await exposedTiles.evaluateAll(els => {
      return els.map((el, i) => ({
        index: i,
        src: el.querySelector('img').src
      }));
    });

    // Find two tiles with same image
    let pair = null;
    for (let i = 0; i < tileData.length && !pair; i++) {
      for (let j = i + 1; j < tileData.length && !pair; j++) {
        if (tileData[i].src === tileData[j].src) {
          pair = [tileData[i].index, tileData[j].index];
        }
      }
    }

    expect(pair).not.toBeNull();

    // Click first tile
    await exposedTiles.nth(pair[0]).click();
    await expect(exposedTiles.nth(pair[0])).toHaveClass(/selected/);

    // Click second tile
    await exposedTiles.nth(pair[1]).click();

    // Wait for match animation
    await page.waitForTimeout(600);

    // Match count should be 1
    const matchCount = await page.locator('#match-count').textContent();
    expect(matchCount).toBe('1');
  });

  test('mismatched tiles deselect after delay', async ({ page }) => {
    const exposedTiles = page.locator('.tile:not(.blocked):not(.matched)');

    // Find two tiles with different images
    const tileData = await exposedTiles.evaluateAll(els => {
      return els.map((el, i) => ({
        index: i,
        src: el.querySelector('img').src
      }));
    });

    let pair = null;
    for (let i = 0; i < tileData.length && !pair; i++) {
      for (let j = i + 1; j < tileData.length && !pair; j++) {
        if (tileData[i].src !== tileData[j].src) {
          pair = [tileData[i].index, tileData[j].index];
        }
      }
    }

    expect(pair).not.toBeNull();

    await exposedTiles.nth(pair[0]).click();
    await exposedTiles.nth(pair[1]).click();

    // Wait for deselect
    await page.waitForTimeout(800);

    // Neither should be selected
    await expect(exposedTiles.nth(pair[0])).not.toHaveClass(/selected/);
    await expect(exposedTiles.nth(pair[1])).not.toHaveClass(/selected/);

    // Match count still 0
    const matchCount = await page.locator('#match-count').textContent();
    expect(matchCount).toBe('0');
  });

  test('switch to 6x6 Flat and New Game', async ({ page }) => {
    await page.locator('button[data-value="6"]').click();
    await page.locator('button[data-value="flat"]').click();
    await page.locator('#new-game-btn').click();

    // Wait for new board
    await page.waitForSelector('.tile', { timeout: 10000 });
    await page.waitForTimeout(300);

    // 6x6 flat = 36 tiles
    const tileCount = await page.locator('.tile').count();
    expect(tileCount).toBe(36);

    // All tiles exposed in flat mode (none blocked)
    const blockedCount = await page.locator('.tile.blocked').count();
    expect(blockedCount).toBe(0);

    const totalPairs = await page.locator('#total-pairs').textContent();
    expect(totalPairs).toBe('18');
  });

  test('switch to 8x8 Stacked and New Game', async ({ page }) => {
    await page.locator('button[data-value="8"]').click();
    await page.locator('button[data-value="stacked"]').click();
    await page.locator('#new-game-btn').click();

    await page.waitForSelector('.tile', { timeout: 10000 });
    await page.waitForTimeout(300);

    // 8x8 stacked = 64+49+64+49+36 = 262 tiles
    const tileCount = await page.locator('.tile').count();
    expect(tileCount).toBe(262);

    const totalPairs = await page.locator('#total-pairs').textContent();
    expect(totalPairs).toBe('131');
  });

  test('New Game reshuffles the board', async ({ page }) => {
    // Record first tile's image
    const firstSrc = await page.locator('.tile').first().evaluate(el => el.querySelector('img').src);

    // Click New Game multiple times — at least one should change
    let changed = false;
    for (let attempt = 0; attempt < 3 && !changed; attempt++) {
      await page.locator('#new-game-btn').click();
      await page.waitForSelector('.tile', { timeout: 10000 });
      await page.waitForTimeout(300);
      const newSrc = await page.locator('.tile').first().evaluate(el => el.querySelector('img').src);
      if (newSrc !== firstSrc) changed = true;
    }
    // This could theoretically be the same by chance, but extremely unlikely over 3 tries
    expect(changed).toBe(true);
  });

  test('matching reveals newly exposed tiles', async ({ page }) => {
    const initialBlockedCount = await page.locator('.tile.blocked').count();

    // Match an exposed pair
    const exposedTiles = page.locator('.tile:not(.blocked):not(.matched)');
    const tileData = await exposedTiles.evaluateAll(els => {
      return els.map((el, i) => ({
        index: i,
        src: el.querySelector('img').src
      }));
    });

    let pair = null;
    for (let i = 0; i < tileData.length && !pair; i++) {
      for (let j = i + 1; j < tileData.length && !pair; j++) {
        if (tileData[i].src === tileData[j].src) {
          pair = [tileData[i].index, tileData[j].index];
        }
      }
    }

    if (pair) {
      await exposedTiles.nth(pair[0]).click();
      await exposedTiles.nth(pair[1]).click();
      await page.waitForTimeout(600);

      const newBlockedCount = await page.locator('.tile.blocked').count();
      // After removing top tiles, some previously blocked tiles may become exposed
      // (blocked count should decrease or stay same, never increase significantly)
      expect(newBlockedCount).toBeLessThanOrEqual(initialBlockedCount);
    }
  });

});
