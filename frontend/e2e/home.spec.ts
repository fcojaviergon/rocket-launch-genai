import { test, expect } from '@playwright/test';

test.describe('Home Page', () => {
  test('should display title and navigation', async ({ page }) => {
    // Navigate to the homepage
    await page.goto('/');
    
    // Check if the title is present
    await expect(page.getByRole('heading', { name: /rocket platform/i })).toBeVisible();
    
    // Verify login button is present
    await expect(page.getByRole('link', { name: /log in/i })).toBeVisible();
    
    // Verify register button is present
    await expect(page.getByRole('link', { name: /register/i })).toBeVisible();
  });

  test('should navigate to login page', async ({ page }) => {
    // Navigate to homepage
    await page.goto('/');
    
    // Click on login button
    await page.getByRole('link', { name: /log in/i }).click();
    
    // Check if we're on the login page
    await expect(page).toHaveURL(/.*login/);
    await expect(page.getByRole('heading', { name: /log in/i })).toBeVisible();
  });

  test('should navigate to register page', async ({ page }) => {
    // Navigate to homepage
    await page.goto('/');
    
    // Click on register button
    await page.getByRole('link', { name: /register/i }).click();
    
    // Check if we're on the register page
    await expect(page).toHaveURL(/.*register/);
    await expect(page.getByRole('heading', { name: /create account/i })).toBeVisible();
  });
}); 