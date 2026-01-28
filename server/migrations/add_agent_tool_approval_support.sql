-- Migration: Add agent tool approval support
-- Created: 2026-01-23
-- Description: Adds tool-specific columns to steps table and creates tool_approvals table

-- Add tool-specific columns to steps table
ALTER TABLE steps
ADD COLUMN IF NOT EXISTS tool_name VARCHAR(255),
ADD COLUMN IF NOT EXISTS tool_call_id VARCHAR(255),
ADD COLUMN IF NOT EXISTS tool_input JSONB,
ADD COLUMN IF NOT EXISTS tool_output JSONB,
ADD COLUMN IF NOT EXISTS agent_state JSONB;

-- Create indexes for tool columns
CREATE INDEX IF NOT EXISTS idx_steps_tool_name ON steps(tool_name);
CREATE INDEX IF NOT EXISTS idx_steps_tool_call_id ON steps(tool_call_id);

-- Create tool_approvals table
CREATE TABLE IF NOT EXISTS tool_approvals (
    id UUID PRIMARY KEY,
    run_id UUID NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    step_id UUID NOT NULL REFERENCES steps(id) ON DELETE CASCADE,
    tool_name VARCHAR(255) NOT NULL,
    tool_call_id VARCHAR(255) NOT NULL,
    tool_arguments JSONB NOT NULL DEFAULT '{}',
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    requested_at TIMESTAMP WITH TIME ZONE NOT NULL,
    timeout_at TIMESTAMP WITH TIME ZONE NOT NULL,
    resolved_at TIMESTAMP WITH TIME ZONE,
    resolved_by VARCHAR(255),
    rejection_reason TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Create indexes for tool_approvals
CREATE INDEX IF NOT EXISTS idx_tool_approvals_run_id ON tool_approvals(run_id);
CREATE INDEX IF NOT EXISTS idx_tool_approvals_step_id ON tool_approvals(step_id);
CREATE INDEX IF NOT EXISTS idx_tool_approvals_tool_name ON tool_approvals(tool_name);
CREATE INDEX IF NOT EXISTS idx_tool_approvals_tool_call_id ON tool_approvals(tool_call_id);
CREATE INDEX IF NOT EXISTS idx_tool_approvals_status ON tool_approvals(status);
CREATE INDEX IF NOT EXISTS idx_tool_approvals_timeout_at ON tool_approvals(timeout_at);

-- Add comment to table
COMMENT ON TABLE tool_approvals IS 'Human-in-the-Loop approval requests for agent tool execution';
COMMENT ON COLUMN tool_approvals.tool_name IS 'Name of the tool requiring approval';
COMMENT ON COLUMN tool_approvals.tool_call_id IS 'Unique identifier for this tool call';
COMMENT ON COLUMN tool_approvals.status IS 'Approval status: pending, approved, rejected, timeout';
COMMENT ON COLUMN tool_approvals.timeout_at IS 'When the approval request expires';
