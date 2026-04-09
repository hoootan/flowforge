"""Add agent team platform: agents, tasks, comments, notifications, skill_templates tables + enabled_skills columns."""

# Migration metadata
MIGRATION_ID = "add_agent_team_platform"
MIGRATION_DATE = "2026-04-10"
DESCRIPTION = "Add agents, tasks, comments, notifications, skill_templates tables and enabled_skills on functions/agents"


async def up(session) -> None:
    """Apply migration."""

    # ── Agents table ──────────────────────────────────────────
    await session.execute(
        """
        CREATE TABLE IF NOT EXISTS agents (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            name VARCHAR(255) NOT NULL,
            slug VARCHAR(255) NOT NULL,
            avatar_url TEXT,
            description TEXT,
            status VARCHAR(20) NOT NULL DEFAULT 'offline',
            model VARCHAR(100),
            system_prompt TEXT,
            capabilities JSONB NOT NULL DEFAULT '{}',
            enabled_skills JSONB,
            config JSONB NOT NULL DEFAULT '{}',
            stats JSONB NOT NULL DEFAULT '{}',
            is_active BOOLEAN DEFAULT true,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            UNIQUE(tenant_id, slug)
        );
        """
    )
    await session.execute("CREATE INDEX IF NOT EXISTS ix_agents_tenant_id ON agents(tenant_id);")
    await session.execute("CREATE INDEX IF NOT EXISTS ix_agents_slug ON agents(slug);")
    await session.execute("CREATE INDEX IF NOT EXISTS ix_agents_status ON agents(status);")

    # ── Tasks table ───────────────────────────────────────────
    await session.execute(
        """
        CREATE TABLE IF NOT EXISTS tasks (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            identifier VARCHAR(20) NOT NULL,
            sequence INTEGER NOT NULL,
            title VARCHAR(500) NOT NULL,
            description TEXT,
            status VARCHAR(20) NOT NULL DEFAULT 'todo',
            priority VARCHAR(20) NOT NULL DEFAULT 'none',
            labels JSONB NOT NULL DEFAULT '[]',
            assignee_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
            assignee_agent_id UUID REFERENCES agents(id) ON DELETE SET NULL,
            created_by_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
            parent_task_id UUID REFERENCES tasks(id) ON DELETE SET NULL,
            function_id UUID REFERENCES functions(id) ON DELETE SET NULL,
            run_id UUID REFERENCES runs(id) ON DELETE SET NULL,
            metadata JSONB NOT NULL DEFAULT '{}',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            UNIQUE(tenant_id, identifier)
        );
        """
    )
    await session.execute("CREATE INDEX IF NOT EXISTS ix_tasks_tenant_id ON tasks(tenant_id);")
    await session.execute("CREATE INDEX IF NOT EXISTS ix_tasks_status ON tasks(status);")
    await session.execute("CREATE INDEX IF NOT EXISTS ix_tasks_assignee_user ON tasks(assignee_user_id);")
    await session.execute("CREATE INDEX IF NOT EXISTS ix_tasks_assignee_agent ON tasks(assignee_agent_id);")
    await session.execute("CREATE INDEX IF NOT EXISTS ix_tasks_parent ON tasks(parent_task_id);")

    # ── Comments table ────────────────────────────────────────
    await session.execute(
        """
        CREATE TABLE IF NOT EXISTS comments (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            task_id UUID REFERENCES tasks(id) ON DELETE CASCADE,
            run_id UUID REFERENCES runs(id) ON DELETE CASCADE,
            author_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
            author_agent_id UUID REFERENCES agents(id) ON DELETE SET NULL,
            content TEXT NOT NULL,
            comment_type VARCHAR(30) NOT NULL DEFAULT 'comment',
            mentions JSONB NOT NULL DEFAULT '[]',
            reactions JSONB NOT NULL DEFAULT '{}',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """
    )
    await session.execute("CREATE INDEX IF NOT EXISTS ix_comments_task_id ON comments(task_id);")
    await session.execute("CREATE INDEX IF NOT EXISTS ix_comments_run_id ON comments(run_id);")

    # ── Notifications table ───────────────────────────────────
    await session.execute(
        """
        CREATE TABLE IF NOT EXISTS notifications (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            notification_type VARCHAR(50) NOT NULL,
            title VARCHAR(500) NOT NULL,
            body TEXT,
            resource_type VARCHAR(50),
            resource_id VARCHAR(255),
            data JSONB NOT NULL DEFAULT '{}',
            is_read BOOLEAN DEFAULT false,
            is_archived BOOLEAN DEFAULT false,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """
    )
    await session.execute("CREATE INDEX IF NOT EXISTS ix_notifications_user_id ON notifications(user_id);")
    await session.execute("CREATE INDEX IF NOT EXISTS ix_notifications_type ON notifications(notification_type);")
    await session.execute("CREATE INDEX IF NOT EXISTS ix_notifications_is_read ON notifications(is_read);")

    # ── Skill Templates table ─────────────────────────────────
    await session.execute(
        """
        CREATE TABLE IF NOT EXISTS skill_templates (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
            name VARCHAR(255) NOT NULL,
            slug VARCHAR(255) NOT NULL,
            description TEXT,
            category VARCHAR(100),
            icon VARCHAR(50),
            version INTEGER NOT NULL DEFAULT 1,
            function_config JSONB NOT NULL DEFAULT '{}',
            tools_config JSONB NOT NULL DEFAULT '[]',
            usage_count INTEGER NOT NULL DEFAULT 0,
            is_builtin BOOLEAN DEFAULT false,
            is_active BOOLEAN DEFAULT true,
            tags JSONB NOT NULL DEFAULT '[]',
            source VARCHAR(20) NOT NULL DEFAULT 'local',
            instructions TEXT,
            source_metadata JSONB,
            created_by_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            UNIQUE(tenant_id, slug)
        );
        """
    )
    await session.execute("CREATE INDEX IF NOT EXISTS ix_skill_templates_tenant_id ON skill_templates(tenant_id);")
    await session.execute("CREATE INDEX IF NOT EXISTS ix_skill_templates_slug ON skill_templates(slug);")
    await session.execute("CREATE INDEX IF NOT EXISTS ix_skill_templates_category ON skill_templates(category);")
    await session.execute("CREATE INDEX IF NOT EXISTS ix_skill_templates_source ON skill_templates(source);")

    # ── Add enabled_skills column to functions table ──────────
    await session.execute(
        """
        ALTER TABLE functions
        ADD COLUMN IF NOT EXISTS enabled_skills JSONB;
        """
    )

    await session.commit()


async def down(session) -> None:
    """Rollback migration."""
    await session.execute("ALTER TABLE functions DROP COLUMN IF EXISTS enabled_skills;")
    await session.execute("DROP TABLE IF EXISTS skill_templates CASCADE;")
    await session.execute("DROP TABLE IF EXISTS notifications CASCADE;")
    await session.execute("DROP TABLE IF EXISTS comments CASCADE;")
    await session.execute("DROP TABLE IF EXISTS tasks CASCADE;")
    await session.execute("DROP TABLE IF EXISTS agents CASCADE;")
    await session.commit()
