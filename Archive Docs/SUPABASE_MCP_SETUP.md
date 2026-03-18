# Supabase MCP Setup Guide

## Overview
This guide will help you set up the Supabase MCP (Model Context Protocol) integration so Claude Code can directly interact with your Supabase database.

## Prerequisites
- Supabase project already created (✓ You have this)
- Claude Code installed in Cursor (✓ You have this)

## Step 1: Get Your Supabase Access Token

1. Go to your Supabase account settings:
   https://supabase.com/dashboard/account/tokens

2. Click "Generate New Token"

3. Give it a name like "Claude Code MCP"

4. Copy the token (it will look like `sbp_xxx...`)

5. Update your `.env` file:
   ```bash
   SUPABASE_ACCESS_TOKEN=sbp_your_actual_token_here
   ```

## Step 2: Verify MCP Configuration

The following files have been created/updated:

### `.claude.json`
```json
{
  "mcpServers": {
    "supabase": {
      "type": "http",
      "url": "https://mcp.supabase.com/mcp"
    }
  }
}
```

### `.env` (Updated)
```bash
SUPABASE_PROJECT_REF=your-supabase-project-ref
SUPABASE_ACCESS_TOKEN=<YOUR_PERSONAL_ACCESS_TOKEN_HERE>
```

## Step 3: Restart Cursor

After updating the `.env` file with your access token:

1. Close and reopen Cursor/Claude Code
2. This ensures the new MCP configuration is loaded

## Step 4: Test MCP Connection

In Claude Code chat, type:
```
/mcp
```

You should see `supabase` listed as an available MCP server.

## Step 5: Run Database Migrations

Once MCP is connected, Claude can run the migrations directly by:

1. Reading the migration files in `backend/migrations/`
2. Using the Supabase MCP to execute SQL directly on your database
3. Verifying the schema changes

## What This Enables

With Supabase MCP connected, Claude Code can:

✅ Inspect your database schema
✅ Run SQL migrations
✅ Query data for debugging
✅ Generate typed queries based on your actual schema
✅ Add/modify RLS policies
✅ Create indexes and optimize queries

## Troubleshooting

### MCP not showing up
- Verify `.claude.json` exists in repo root
- Restart Cursor completely
- Check that file has valid JSON syntax

### Authentication errors
- Verify `SUPABASE_ACCESS_TOKEN` is set correctly
- Check token hasn't expired
- Ensure `SUPABASE_PROJECT_REF` matches your project (your-supabase-project-ref)

### Permission errors
- Access token needs sufficient permissions
- May need to use a service role key for some operations

## Next Steps

After MCP is connected, I can:

1. Run all 4 database migrations automatically
2. Verify the schema matches the PRD requirements
3. Continue with Phase 1.2: Creating job_config.py
4. Proceed through the full TEP implementation plan

## Security Note

- Keep `.env` file out of git (already in .gitignore)
- Never commit access tokens to version control
- Rotate tokens periodically for security
