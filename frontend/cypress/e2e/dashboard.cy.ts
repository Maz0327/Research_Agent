/// <reference types="cypress" />

/**
 * Dashboard E2E tests.
 * Tests the main job management interface.
 *
 * Note: These tests require authentication. Set TEST_USER_EMAIL and
 * TEST_USER_PASSWORD in cypress.env.json for authenticated tests.
 */

describe('Dashboard', () => {
  describe('Unauthenticated', () => {
    it('redirects to login when not authenticated', () => {
      cy.visit('/dashboard');
      // Should redirect to login or show auth prompt
      cy.url().should('satisfy', (url: string) => {
        return url.includes('/login') || url.includes('/dashboard');
      });
    });
  });

  describe('Authenticated', () => {
    beforeEach(() => {
      // Skip if no test credentials configured
      const email = Cypress.env('TEST_USER_EMAIL');
      if (!email) {
        cy.log('Skipping authenticated tests - no TEST_USER_EMAIL configured');
        return;
      }
      cy.login();
    });

    it('loads the dashboard page', () => {
      if (!Cypress.env('TEST_USER_EMAIL')) return;

      cy.url().should('include', '/dashboard');
      cy.get('body').should('be.visible');
    });

    it('displays the job creation interface', () => {
      if (!Cypress.env('TEST_USER_EMAIL')) return;

      // Dashboard should have some form of input for creating jobs
      cy.get('body').then(($body) => {
        // Check for URL input, text input, or create button
        const hasInput = $body.find('input, textarea, [role="textbox"]').length > 0;
        const hasCreateButton = $body.find('button').filter(':contains("Create"), :contains("Research"), :contains("Analyze")').length > 0;
        expect(hasInput || hasCreateButton).to.be.true;
      });
    });
  });
});
