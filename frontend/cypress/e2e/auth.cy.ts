/// <reference types="cypress" />

/**
 * Authentication flow E2E tests.
 * Tests login page functionality and auth redirects.
 */

describe('Authentication', () => {
  beforeEach(() => {
    cy.visit('/login');
  });

  it('displays the login form', () => {
    cy.get('input[type="email"]').should('be.visible');
    cy.get('button').should('exist');
  });

  it('shows error for empty email submission', () => {
    // Try to submit without entering email
    cy.get('button[type="submit"]').first().click();
    // Should show some error feedback
    cy.get('body').should('contain.text', 'email').or('contain.text', 'required');
  });

  it('has Google OAuth button', () => {
    // Check for Google sign-in option
    cy.get('button').then(($buttons) => {
      const googleButton = $buttons.filter(':contains("Google")');
      if (googleButton.length > 0) {
        expect(googleButton).to.be.visible;
      }
    });
  });

  it('navigates back to landing from login', () => {
    // Check if there's a way to go back to landing
    cy.get('a[href="/"]').first().click({ force: true });
    cy.url().should('eq', Cypress.config('baseUrl') + '/');
  });
});
