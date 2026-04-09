/**
 * FlowForge TypeScript Client - Skills Resource
 */

import type { RequestFn } from "../builder";
import type { Result } from "../types";

export interface Skill {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  category: string | null;
  icon: string | null;
  version: number;
  function_config: Record<string, unknown>;
  tools_config: Record<string, unknown>[];
  usage_count: number;
  is_builtin: boolean;
  is_active: boolean;
  tags: string[];
  source: "local" | "skills_sh" | "github";
  instructions: string | null;
  source_metadata: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export interface CreateSkillInput {
  name: string;
  description?: string;
  category?: string;
  icon?: string;
  function_config?: Record<string, unknown>;
  tools_config?: Record<string, unknown>[];
  tags?: string[];
}

export interface ImportSkillInput {
  repo: string;
  path?: string;
  source?: string;
  external_id?: string;
  name_override?: string;
  category?: string;
  tags?: string[];
}

export interface MarketplaceSearchResult {
  external_id: string;
  name: string;
  description: string;
  source: string;
  repo: string;
  install_count: number;
  preview_url: string | null;
}

export interface MarketplaceSearchResponse {
  results: MarketplaceSearchResult[];
  total: number;
}

export interface SkillPreview {
  name: string;
  description: string;
  raw_content: string;
  frontmatter: Record<string, unknown>;
  body: string;
  repo: string;
  path: string;
}

export interface SkillListResponse {
  skills: Skill[];
  total: number;
}

export class SkillsResource {
  constructor(private request: RequestFn) {}

  async list(params?: { category?: string; search?: string; source?: string }): Promise<Result<SkillListResponse>> {
    const query = new URLSearchParams();
    if (params?.category) query.set("category", params.category);
    if (params?.search) query.set("search", params.search);
    if (params?.source) query.set("source", params.source);
    const qs = query.toString();
    return this.request<SkillListResponse>("GET", `/skills${qs ? `?${qs}` : ""}`);
  }

  async get(skillId: string): Promise<Result<Skill>> {
    return this.request<Skill>("GET", `/skills/${skillId}`);
  }

  async create(data: CreateSkillInput): Promise<Result<Skill>> {
    return this.request<Skill>("POST", "/skills", data);
  }

  async update(skillId: string, data: Partial<CreateSkillInput>): Promise<Result<Skill>> {
    return this.request<Skill>("PATCH", `/skills/${skillId}`, data);
  }

  async use(skillId: string): Promise<Result<{ function_config: Record<string, unknown>; tools_config: Record<string, unknown>[]; instructions?: string; system_prompt_append?: string }>> {
    return this.request<{ function_config: Record<string, unknown>; tools_config: Record<string, unknown>[]; instructions?: string; system_prompt_append?: string }>("POST", `/skills/${skillId}/use`);
  }

  async delete(skillId: string): Promise<Result<{ success: boolean }>> {
    return this.request<{ success: boolean }>("DELETE", `/skills/${skillId}`);
  }

  // ── Marketplace ─────────────────────────────────────────────

  async searchMarketplace(params: { q: string; source?: string; limit?: number }): Promise<Result<MarketplaceSearchResponse>> {
    const query = new URLSearchParams();
    query.set("q", params.q);
    if (params.source) query.set("source", params.source);
    if (params.limit) query.set("limit", String(params.limit));
    return this.request<MarketplaceSearchResponse>("GET", `/skills/marketplace/search?${query.toString()}`);
  }

  async preview(repo: string, path: string = "SKILL.md"): Promise<Result<SkillPreview>> {
    const query = new URLSearchParams();
    query.set("repo", repo);
    query.set("path", path);
    return this.request<SkillPreview>("GET", `/skills/marketplace/preview?${query.toString()}`);
  }

  async import(data: ImportSkillInput): Promise<Result<Skill>> {
    return this.request<Skill>("POST", "/skills/marketplace/import", data);
  }

  async refresh(skillId: string): Promise<Result<Skill>> {
    return this.request<Skill>("POST", `/skills/${skillId}/refresh`);
  }
}
