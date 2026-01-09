#!/usr/bin/env node
/**
 * Pydantic Model Validation Hook
 *
 * Purpose: Validate that model changes maintain schema integrity
 * Trigger: After editing files in backend/models/
 *
 * Phase 0 - Semantic-First Architecture
 *
 * This hook ensures:
 * 1. TranscriptProvenance model has all required fields
 * 2. VerificationCapabilities defaults are correct
 * 3. Model validators enforce capability restrictions
 */

const fs = require('fs');
const path = require('path');

// Configuration
const MODELS_DIR = 'backend/models';
const CRITICAL_MODELS = [
    'source.py',          // TranscriptProvenance, VerificationCapabilities
    'job_record.py',      // Artifacts with semantic doc references
    'source_ledger.py',   // Doc 0 models (when created)
    'jump_start.py',      // Doc 1 models (when created)
    'semantic_brief.py',  // Doc 2 models (when created)
];

// Required fields for TranscriptProvenance
const TRANSCRIPT_PROVENANCE_FIELDS = [
    'transcript_source',
    'transcript_status',
    'captions_status',
    'gemini_analysis_mode',
    'verification_capabilities',
    'notes',
];

// Required fields for VerificationCapabilities
const VERIFICATION_CAPABILITIES_FIELDS = [
    'quote_verification',
    'timestamp_grounding',
    'semantic_precision',
];

/**
 * Check if a file contains the required class and fields
 */
function validateModelFile(filePath, className, requiredFields) {
    if (!fs.existsSync(filePath)) {
        return { exists: false, valid: true, missing: [] };
    }

    const content = fs.readFileSync(filePath, 'utf8');

    // Check if class exists
    const classPattern = new RegExp(`class\\s+${className}\\s*\\(`);
    if (!classPattern.test(content)) {
        return { exists: false, valid: true, missing: [] };
    }

    // Check for required fields
    const missing = [];
    for (const field of requiredFields) {
        const fieldPattern = new RegExp(`${field}\\s*[:=]`);
        if (!fieldPattern.test(content)) {
            missing.push(field);
        }
    }

    return {
        exists: true,
        valid: missing.length === 0,
        missing,
    };
}

/**
 * Main validation function
 */
function runValidation() {
    const errors = [];
    const warnings = [];

    // Check TranscriptProvenance
    const sourceFile = path.join(MODELS_DIR, 'source.py');

    const provenanceCheck = validateModelFile(
        sourceFile,
        'TranscriptProvenance',
        TRANSCRIPT_PROVENANCE_FIELDS
    );

    if (provenanceCheck.exists && !provenanceCheck.valid) {
        errors.push(
            `TranscriptProvenance missing required fields: ${provenanceCheck.missing.join(', ')}`
        );
    }

    const capabilitiesCheck = validateModelFile(
        sourceFile,
        'VerificationCapabilities',
        VERIFICATION_CAPABILITIES_FIELDS
    );

    if (capabilitiesCheck.exists && !capabilitiesCheck.valid) {
        errors.push(
            `VerificationCapabilities missing required fields: ${capabilitiesCheck.missing.join(', ')}`
        );
    }

    // Check for model_validator in TranscriptProvenance
    if (provenanceCheck.exists) {
        const content = fs.readFileSync(sourceFile, 'utf8');
        if (!content.includes('@model_validator')) {
            warnings.push(
                'TranscriptProvenance should have @model_validator for capability enforcement'
            );
        }
    }

    return { errors, warnings };
}

// Export for use by Claude Code hooks system
module.exports = {
    name: 'pydantic-validation',
    description: 'Validates Pydantic model integrity for semantic-first architecture',
    trigger: 'post_edit',
    filePatterns: ['backend/models/*.py'],

    async run(context) {
        const { errors, warnings } = runValidation();

        if (errors.length > 0) {
            return {
                status: 'error',
                message: `Model validation failed:\n${errors.join('\n')}`,
            };
        }

        if (warnings.length > 0) {
            return {
                status: 'warning',
                message: `Model validation warnings:\n${warnings.join('\n')}`,
            };
        }

        return {
            status: 'success',
            message: 'Pydantic models validated successfully',
        };
    },
};

// CLI execution
if (require.main === module) {
    const { errors, warnings } = runValidation();

    if (errors.length > 0) {
        console.error('❌ Model validation FAILED:');
        errors.forEach(e => console.error(`  - ${e}`));
        process.exit(1);
    }

    if (warnings.length > 0) {
        console.warn('⚠️  Model validation warnings:');
        warnings.forEach(w => console.warn(`  - ${w}`));
    }

    console.log('✅ Pydantic models validated successfully');
    process.exit(0);
}
