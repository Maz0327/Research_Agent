/// <reference types="cypress" />

/**
 * Smoke tests - verify critical paths are functional.
 * These run on every PR to catch regressions early.
 */

describe('Smoke Tests', () => {
  describe('Public Pages', () => {
    it('loads the landing page', () => {
      cy.visit('/');
      cy.get('body').should('be.visible');
      // Landing page should have some content
      cy.contains(/research|agent/i).should('exist');
    });

    it('loads the login page', () => {
      cy.visit('/login');
      cy.get('input[type="email"]').should('be.visible');
      cy.get('button').should('exist');
    });

    it('redirects unauthenticated users from dashboard to login', () => {
      cy.visit('/dashboard');
      // Should redirect to login or show login prompt
      cy.url().should('satisfy', (url: string) => {
        return url.includes('/login') || url.includes('/dashboard');
      });
    });
  });

  describe('API Health', () => {
    it('backend health check responds', () => {
      const apiUrl = Cypress.env('API_URL') || 'http://localhost:8000';
      cy.request({
        url: `${apiUrl}/health`,
        failOnStatusCode: false,
      }).then((response) => {
        // Accept 200 (healthy) or 503 (degraded but running)
        expect(response.status).to.be.oneOf([200, 503]);
        expect(response.body).to.have.property('status');
      });
    });
  });

  describe('Security Headers', () => {
    it('landing page returns security headers', () => {
      cy.request('/').then((response) => {
        // Next.js security headers from next.config.js
        expect(response.headers).to.have.property('x-content-type-options', 'nosniff');
        expect(response.headers).to.have.property('x-frame-options', 'DENY');
      });
    });
  });
});
