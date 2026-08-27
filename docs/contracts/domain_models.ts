/**
 * MoodFeed Production Domain Contracts
 * Version: 1.0.0
 * Architecture: Event-driven / REST Modular Monolith
 * Privacy Classification Standards:
 * - PUBLIC: Publicly visible or non-sensitive data
 * - INTERNAL: System-generated identifiers and operational state
 * - CONFIDENTIAL_PII: Personally Identifiable Information (User profile, auth credentials)
 * - RESTRICTED: Sensitive user interactions and privacy preferences
 */

// ==========================================
// 1. Core User, Session & Consent Models
// ==========================================

export type UserRole = "user" | "moderator" | "admin" | "system";
export type AccountStatus = "active" | "suspended" | "pending_verification" | "marked_for_deletion";

/**
 * User Entity
 * Privacy Classification: CONFIDENTIAL_PII
 * Owner: User
 */
export interface User {
  id: string; // UUID v4
  email: string; // RFC 5322 email validation
  displayName: string; // Max 50 chars, sanitized
  role: UserRole;
  status: AccountStatus;
  createdAt: string; // ISO 8601 UTC
  updatedAt: string; // ISO 8601 UTC
  lastLoginAt?: string; // ISO 8601 UTC
}

/**
 * Session Entity
 * Privacy Classification: CONFIDENTIAL_PII
 * Owner: User (1:N)
 */
export interface Session {
  id: string; // UUID v4 (Session Token ID)
  userId: string; // Foreign key -> User.id
  tokenFamily: string; // Refresh token rotation family
  ipAddressHash: string; // SHA-256 salted hash of client IP (no raw IP)
  userAgent: string; // Client user agent string
  expiresAt: string; // ISO 8601 UTC
  createdAt: string; // ISO 8601 UTC
  revoked: boolean;
}

export type ConsentType =
  | "connected_source_processing"
  | "client_side_ranking"
  | "anonymous_telemetry"
  | "pilot_evaluation";

export type ConsentStatus = "granted" | "revoked" | "expired";

/**
 * Consent Entity (GDPR / KVKK compliance audit trail)
 * Privacy Classification: RESTRICTED
 * Owner: User (1:N)
 */
export interface Consent {
  id: string; // UUID v4
  userId: string; // Foreign key -> User.id
  consentType: ConsentType;
  status: ConsentStatus;
  version: string; // e.g. "2026.1"
  grantedAt: string; // ISO 8601 UTC
  revokedAt?: string; // ISO 8601 UTC
  expiresAt?: string; // ISO 8601 UTC (optional auto-expiry)
}

// ==========================================
// 2. User Preferences & Muting
// ==========================================

export type RepetitionSensitivity = "low" | "medium" | "high";
export type NegativitySensitivity = "show" | "reduce" | "hide";
export type IntensitySensitivity = "low" | "balanced" | "high";
export type DiversityPreference = "diverse" | "balanced" | "allow_similar";
export type ExplanationDisplayMode = "feed_cards" | "detail_only" | "off";
export type ActiveFeedMode = "moodfeed" | "original";
export type RankingProfilePreset = "balanced" | "calmer" | "user_control" | "custom";

/**
 * User Preferences Entity
 * Privacy Classification: RESTRICTED
 * Owner: User (1:1)
 */
export interface UserPreferences {
  id: string; // UUID v4
  userId: string; // Foreign key -> User.id
  profilePreset: RankingProfilePreset;
  repetitionSensitivity: RepetitionSensitivity;
  negativitySensitivity: NegativitySensitivity;
  intensitySensitivity: IntensitySensitivity;
  diversityPreference: DiversityPreference;
  groupingEnabled: boolean;
  lowIntensityMode: boolean;
  showExplanations: ExplanationDisplayMode;
  activeFeedMode: ActiveFeedMode;
  updatedAt: string; // ISO 8601 UTC
}

/**
 * Muted Source Entity
 * Privacy Classification: RESTRICTED
 * Owner: User (1:N)
 */
export interface MutedSource {
  id: string; // UUID v4
  userId: string; // Foreign key -> User.id
  sourceIdentifier: string; // Handle, Channel ID or Platform Author Key
  sourceDisplayName: string;
  mutedAt: string; // ISO 8601 UTC
}

/**
 * Saved Item Entity
 * Privacy Classification: RESTRICTED
 * Owner: User (1:N)
 */
export interface SavedItem {
  id: string; // UUID v4
  userId: string; // Foreign key -> User.id
  contentId: string; // Foreign key -> ContentItem.id
  savedAt: string; // ISO 8601 UTC
}

// ==========================================
// 3. Content Ingestion, Features & Groups
// ==========================================

export type SentimentPolarity = "positive" | "negative" | "neutral";
export type ToxicityFlag = "clean" | "low" | "moderate" | "high";

/**
 * Extracted Feature Vector for Content
 * Privacy Classification: INTERNAL
 * Owner: ContentItem (1:1)
 */
export interface ContentFeature {
  id: string; // UUID v4
  contentId: string; // Foreign key -> ContentItem.id
  sentimentPolarity: SentimentPolarity;
  sentimentScore: number; // [0.0 - 1.0]
  negativityScore: number; // [0.0 - 1.0]
  toxicityScore: number; // [0.0 - 1.0]
  repetitionScore: number; // [0.0 - 1.0]
  intensityScore: number; // [0.0 - 1.0]
  extractedKeywords: string[];
  extractedAt: string; // ISO 8601 UTC
  modelEngine: "rule_based" | "berturk_v1" | "hybrid";
}

/**
 * Similarity Group Cluster
 * Privacy Classification: INTERNAL
 */
export interface SimilarityGroup {
  id: string; // e.g. "grp-tech-ai", "grp-urban-transport"
  category: string;
  topicTitle: string;
  itemCount: number;
  averageIntensity: number; // [0.0 - 1.0]
  updatedAt: string; // ISO 8601 UTC
}

/**
 * Content Item (Normalized ingested post)
 * Privacy Classification: PUBLIC / INTERNAL
 */
export interface ContentItem {
  id: string; // UUID v4 or canonical post-id (e.g. "post-001")
  sourceId: string; // Foreign key -> Source / Platform ID
  sourceLabel: string;
  authorName: string;
  authorAvatarUrl?: string;
  category: string;
  title: string;
  summary: string;
  bodyText: string;
  publishedAt: string; // ISO 8601 UTC
  tags: string[];
  similarityGroupId?: string;
  originalPlatformRank: number; // 1-based original index
  originalPlatformScore: number; // [0.0 - 1.0]
  isSyntheticDemo: boolean; // Flag to identify demo seeds vs ingested
}

// ==========================================
// 4. Ranking, Explanations & Feedback
// ==========================================

export interface ScoreBreakdown {
  originalScore: number; // S_orig
  toxicityPenalty: number; // W_tox * T
  negativityPenalty: number; // W_neg * N * R
  diversityBonus: number; // W_div * D * R
  finalScore: number; // Clamped [0.0 - 1.0]
}

export interface RankExplanation {
  observed: string; // What signal pattern was detected
  action: string; // How MoodFeed adjusted the rank
  control: string; // Available user controls (Undo, Mute, Preferences)
  limitation: string; // Non-clinical ethical disclaimer
  mathematicalFormula: string;
  scoreBreakdown: ScoreBreakdown;
}

/**
 * Feed Item (Decorated content for presentation)
 * Privacy Classification: RESTRICTED (per session/user)
 */
export interface FeedItem {
  content: ContentItem;
  feature: ContentFeature;
  originalRank: number;
  moodfeedRank: number;
  activeRank: number; // Based on activeFeedMode and user undo state
  rankDelta: number; // originalRank - activeRank
  rankReason: string;
  explanation: RankExplanation;
  isSaved: boolean;
  isReverted: boolean;
  isMuted: boolean;
}

export interface FeedResponse {
  items: FeedItem[];
  totalCount: number;
  page: number;
  pageSize: number;
  hasMore: boolean;
  activeProfile: RankingProfilePreset;
  activeFeedMode: ActiveFeedMode;
  activeScenario: string;
  spiralRiskScore: number; // [0.0 - 1.0]
  spiralRiskLevel: "low" | "moderate" | "high";
  scorerMode: "rule_based" | "berturk" | "rule_based_fallback";
  processingTimeMs: number;
  generatedAt: string; // ISO 8601 UTC
}

export type FeedbackAction = "undo_recommendation" | "apply_recommendation" | "reduce_similar" | "report_inaccuracy";

/**
 * Recommendation Feedback Entity
 * Privacy Classification: RESTRICTED
 * Owner: User (1:N)
 */
export interface RecommendationFeedback {
  id: string; // UUID v4
  userId: string;
  contentId: string;
  action: FeedbackAction;
  originalRank: number;
  proposedRank: number;
  activePreferenceProfile: string;
  createdAt: string; // ISO 8601 UTC
}

// ==========================================
// 5. Insights, Pilot Evaluation & Reports
// ==========================================

export interface CategoryMetric {
  category: string;
  count: number;
  percentage: number;
}

export interface SimilarityGroupMetric {
  groupTitle: string;
  count: number;
  intensityLevel: "düşük" | "orta" | "yüksek";
}

/**
 * Insights Summary
 * Privacy Classification: RESTRICTED
 */
export interface InsightsSummary {
  period: "session" | "daily" | "weekly";
  totalContentsAnalyzed: number;
  uniqueSourcesCount: number;
  uniqueCategoriesCount: number;
  similarityGroupsCount: number;
  highRepetitionCount: number;
  highNegativityCount: number;
  highIntensityCount: number;
  savedItemsCount: number;
  revertedRecommendationsCount: number;
  mutedSourcesCount: number;
  rankChangedCount: number;
  categoryDistribution: CategoryMetric[];
  similarityGroupDistribution: SimilarityGroupMetric[];
  nonClinicalDisclaimer: string;
  generatedAt: string; // ISO 8601 UTC
}

export interface TaskQualityMetric {
  taskKey: string;
  taskName: string;
  status: "pending" | "active" | "completed" | "skipped";
  startedAt: number | null; // Epoch ms
  completedAt: number | null; // Epoch ms
  durationMs: number;
  errorCount: number;
  retryCount: number;
}

/**
 * Pilot Evaluation Session Entity
 * Privacy Classification: RESTRICTED / ANONYMOUS
 */
export interface PilotSession {
  sessionId: string; // UUID or anonymous identifier
  consentGiven: boolean;
  consentTimestamp: string | null;
  startedAt: string | null;
  completedAt: string | null;
  tasksCompleted: Record<string, boolean>;
  taskQualityMetrics: Record<string, TaskQualityMetric>;
  surveyLikertRatings: {
    understandability?: number; // 1-5
    explainability?: number; // 1-5
    userControl?: number; // 1-5
    trust?: number; // 1-5
    willingness?: number; // 1-5
    benefit?: number; // 1-5
  };
  surveyOpenFeedback: {
    likedAspects?: string;
    confusingAspects?: string;
    suggestedImprovements?: string;
  };
  isCompleted: boolean;
}

export interface ExportReport {
  reportType: "exploratory_prototype_feedback" | "user_data_archive";
  generatedAt: string;
  syntheticDataWarning: string;
  noClinicalClaim: string;
  noGeneralizationClaim: string;
  dataRetentionPolicy: "memory_only" | "user_controlled";
  session: {
    anonymousSessionId: string;
    sessionDurationSeconds: number;
    revertedCount: number;
    contentCount: number;
    contentRemoved: 0; // Invariant: MoodFeed never deletes content
    tasksCompleted: Record<string, boolean>;
    taskQualityMetrics: Record<string, TaskQualityMetric>;
    surveyLikertRatings: Record<string, number>;
    surveyOpenText: Record<string, string>;
  };
}

// ==========================================
// 6. Global API Error Model
// ==========================================

export interface ApiErrorDetail {
  field?: string;
  message: string;
  code: string;
}

export interface ApiError {
  error: {
    code: string; // e.g. "UNAUTHORIZED", "VALIDATION_FAILED", "RESOURCE_NOT_FOUND", "RATE_LIMIT_EXCEEDED"
    message: string;
    details?: ApiErrorDetail[];
    requestId: string; // For distributed tracing
    timestamp: string; // ISO 8601 UTC
  };
}
