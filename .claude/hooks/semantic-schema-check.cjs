#!/usr/bin/env node
/**
 * Semantic Schema Validation Hook
 *
 * Purpose: Ensure JSON outputs conform to semantic-first document schemas
 * Trigger: After editing pipeline output or dual_output files
 *
 * Phase 0 - Semantic-First Architecture
 *
 * This hook validates:
 * 1. Doc 0 (Source Ledger) has required structure
 * 2. Doc 1 (Jump-Start) has minimum depth
 * 3. Doc 2 (Semantic Brief) has proper citations
 * 4. All IDs follow naming scheme
 */

const fs = require('fs');
const path = require('path');

// ID validation patterns
const ID_PATTERNS = {
    source: /^SRC_\d+$/,
    quote: /^QUOTE_\d{3}$/,
    clip: /^CLIP_\d{3}$/,
    claim: /^CLM_\d{3}$/,
    key_point: /^KEY_POINT_\d{3}$/,
    theme: /^THEME_\d{3}$/,
    gap: /^GAP_\d{3}$/,
    lead: /^LEAD_\d{3}$/,
    tension: /^TEN_\d+$/,
};

// Minimum depth requirements
const MINIMUM_DEPTHS = {
    doc0: {
        sources_with_transcript: 1,
        quotes_or_clips: 6,  // 6 quotes OR 10 clips
        tags: 3,
    },
    doc1: {
        gaps: 5,
        leads: 10,
        verification_items: 5,
        open_questions: 5,
    },
    doc2: {
        key_points: 8,
        themes: 4,
        gaps: 5,
    },
};

/**
 * Validate ID format
 */
function validateId(id, type) {
    const pattern = ID_PATTERNS[type];
    if (!pattern) return true; // Unknown type, skip
    return pattern.test(id);
}

/**
 * Validate Doc 0 structure
 */
function validateDoc0(doc) {
    const errors = [];
    const warnings = [];

    // Check topic_lock
    if (!doc.topic_lock) {
        errors.push('Doc 0 missing topic_lock');
    } else {
        if (!doc.topic_lock.one_sentence) {
            warnings.push('topic_lock missing one_sentence');
        }
        if (!doc.topic_lock.in_scope || doc.topic_lock.in_scope.length === 0) {
            warnings.push('topic_lock missing in_scope items');
        }
    }

    // Check sources
    const sources = doc.sources || [];
    if (sources.length === 0) {
        errors.push('Doc 0 has no sources');
    }

    // Check transcript provenance for video sources
    const videoSources = sources.filter(s =>
        s.source_type === 'youtube' || s.source_type === 'video'
    );
    for (const source of videoSources) {
        if (!source.transcript_provenance) {
            errors.push(`Source ${source.source_id || 'unknown'} missing transcript_provenance`);
        }
    }

    // Check minimum quotes/clips
    const quotes = doc.quotes || [];
    const clips = doc.clips || [];
    if (quotes.length < 6 && clips.length < 10) {
        warnings.push(
            `Doc 0 below minimum depth: ${quotes.length} quotes, ${clips.length} clips ` +
            `(need 6+ quotes OR 10+ clips)`
        );
    }

    // Validate IDs
    for (const source of sources) {
        if (source.source_id && !validateId(source.source_id, 'source')) {
            warnings.push(`Invalid source ID format: ${source.source_id}`);
        }
    }
    for (const quote of quotes) {
        if (quote.quote_id && !validateId(quote.quote_id, 'quote')) {
            warnings.push(`Invalid quote ID format: ${quote.quote_id}`);
        }
    }

    return { errors, warnings };
}

/**
 * Validate Doc 1 structure
 */
function validateDoc1(doc) {
    const errors = [];
    const warnings = [];

    // Check minimum gaps
    const gaps = doc.gaps || [];
    if (gaps.length < MINIMUM_DEPTHS.doc1.gaps) {
        warnings.push(`Doc 1 has ${gaps.length} gaps (minimum: ${MINIMUM_DEPTHS.doc1.gaps})`);
    }

    // Check minimum leads
    const leads = doc.leads || [];
    if (leads.length < MINIMUM_DEPTHS.doc1.leads) {
        warnings.push(`Doc 1 has ${leads.length} leads (minimum: ${MINIMUM_DEPTHS.doc1.leads})`);
    }

    // Check top_3_next_steps
    const nextSteps = doc.top_3_next_steps || [];
    if (nextSteps.length !== 3) {
        errors.push(`Doc 1 must have exactly 3 next steps (has ${nextSteps.length})`);
    }

    // Validate IDs
    for (const gap of gaps) {
        if (gap.gap_id && !validateId(gap.gap_id, 'gap')) {
            warnings.push(`Invalid gap ID format: ${gap.gap_id}`);
        }
    }
    for (const lead of leads) {
        if (lead.lead_id && !validateId(lead.lead_id, 'lead')) {
            warnings.push(`Invalid lead ID format: ${lead.lead_id}`);
        }
    }

    return { errors, warnings };
}

/**
 * Validate Doc 2 structure
 */
function validateDoc2(doc) {
    const errors = [];
    const warnings = [];

    // Check minimum key points
    const keyPoints = doc.key_points || [];
    if (keyPoints.length < MINIMUM_DEPTHS.doc2.key_points) {
        warnings.push(`Doc 2 has ${keyPoints.length} key points (minimum: ${MINIMUM_DEPTHS.doc2.key_points})`);
    }

    // Check minimum themes
    const themes = doc.themes || [];
    if (themes.length < MINIMUM_DEPTHS.doc2.themes) {
        warnings.push(`Doc 2 has ${themes.length} themes (minimum: ${MINIMUM_DEPTHS.doc2.themes})`);
    }

    // Check citations on key points
    for (const kp of keyPoints) {
        if (!kp.based_on || kp.based_on.length === 0) {
            if (kp.confidence !== 'speculative') {
                errors.push(
                    `Key point ${kp.key_point_id || 'unknown'} has no citations ` +
                    `and is not marked speculative`
                );
            }
        }
    }

    // Check theme minimum key points
    for (const theme of themes) {
        const relatedKPs = theme.related_key_points || [];
        if (relatedKPs.length < 2) {
            warnings.push(`Theme ${theme.theme_id || 'unknown'} has fewer than 2 related key points`);
        }
    }

    // Validate IDs
    for (const kp of keyPoints) {
        if (kp.key_point_id && !validateId(kp.key_point_id, 'key_point')) {
            warnings.push(`Invalid key point ID format: ${kp.key_point_id}`);
        }
    }
    for (const theme of themes) {
        if (theme.theme_id && !validateId(theme.theme_id, 'theme')) {
            warnings.push(`Invalid theme ID format: ${theme.theme_id}`);
        }
    }

    // Check confidence calibration
    if (!doc.confidence_overall) {
        warnings.push('Doc 2 missing confidence_overall');
    }

    return { errors, warnings };
}

/**
 * Main validation function
 */
function runValidation(jsonData, docType) {
    switch (docType) {
        case 'doc0':
        case 'source_ledger':
            return validateDoc0(jsonData);
        case 'doc1':
        case 'jump_start':
            return validateDoc1(jsonData);
        case 'doc2':
        case 'semantic_brief':
            return validateDoc2(jsonData);
        default:
            return { errors: [], warnings: [`Unknown doc type: ${docType}`] };
    }
}

// Export for use by Claude Code hooks system
module.exports = {
    name: 'semantic-schema-check',
    description: 'Validates semantic-first document schemas',
    trigger: 'post_edit',
    filePatterns: [
        'backend/pipeline/dual_output.py',
        'backend/models/source_ledger.py',
        'backend/models/jump_start.py',
        'backend/models/semantic_brief.py',
    ],

    async run(context) {
        // This hook is primarily documentation-focused
        // Actual runtime validation happens in Python code
        return {
            status: 'success',
            message: 'Semantic schema check configured - see backend validation for runtime checks',
        };
    },

    // Expose validation functions for testing
    validateDoc0,
    validateDoc1,
    validateDoc2,
    validateId,
    runValidation,
    MINIMUM_DEPTHS,
    ID_PATTERNS,
};

// CLI execution for testing
if (require.main === module) {
    const args = process.argv.slice(2);

    if (args.length < 2) {
        console.log('Usage: semantic-schema-check.cjs <doc_type> <json_file>');
        console.log('  doc_type: doc0, doc1, doc2, source_ledger, jump_start, semantic_brief');
        process.exit(0);
    }

    const [docType, jsonFile] = args;

    try {
        const jsonData = JSON.parse(fs.readFileSync(jsonFile, 'utf8'));
        const { errors, warnings } = runValidation(jsonData, docType);

        if (errors.length > 0) {
            console.error('❌ Schema validation FAILED:');
            errors.forEach(e => console.error(`  - ${e}`));
        }

        if (warnings.length > 0) {
            console.warn('⚠️  Schema validation warnings:');
            warnings.forEach(w => console.warn(`  - ${w}`));
        }

        if (errors.length === 0 && warnings.length === 0) {
            console.log('✅ Schema validation passed');
        }

        process.exit(errors.length > 0 ? 1 : 0);
    } catch (e) {
        console.error(`Error: ${e.message}`);
        process.exit(1);
    }
}
