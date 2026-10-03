const { computed, createApp, ref } = Vue;

const configuredApiUrl = typeof window.RESEARCHOS_API_URL === "string"
  ? window.RESEARCHOS_API_URL.trim().replace(/\/$/, "")
  : "";
const API_BASE_URL = ["localhost", "127.0.0.1"].includes(window.location.hostname)
  ? "http://127.0.0.1:8000"
  : configuredApiUrl;
const REQUEST_TIMEOUT_MS = 90_000;
const DEFAULT_TASK = "请说明我要完成的业务目标，并结合这份资料识别重点、风险与下一步行动。";
const ROLE_OPTIONS = [
  { id: "researcher", name: "AI技术专家", workspaceName: "AI技术专家工作空间", description: "分析技术路线、识别技术风险、输出技术建议。", capabilities: ["技术路线分析", "技术风险识别", "技术建议输出"], scenario: "paper", task: "我需要评估这份技术资料的技术路线、核心优势、技术风险和优化方向。" },
  { id: "product_manager", name: "AI产品经理", workspaceName: "AI产品经理工作空间", description: "分析产品资料、发现用户价值、输出产品机会。", capabilities: ["产品资料分析", "用户价值发现", "产品机会输出"], scenario: "product_document", task: "我需要评估这份产品资料的用户痛点、产品机会、功能建议和优先级。" },
  { id: "pre_sales_consultant", name: "AI售前顾问", workspaceName: "AI售前顾问工作空间", description: "分析客户方案、判断方案风险、生成沟通策略。", capabilities: ["技术方案分析", "风险识别", "客户沟通"], scenario: "technical_document", task: "我要准备一次客户技术交流，需要分析该方案优势、风险并生成沟通策略。" },
];
const QUICK_WORKSPACE_TASKS = [
  { id: "customer_meeting", name: "准备客户技术交流", role: "pre_sales_consultant", scenario: "technical_document", task: "我要准备一次客户技术交流，需要分析该方案优势、风险并生成沟通策略。" },
  { id: "competitor_review", name: "分析竞品资料", role: "product_manager", scenario: "product_document", task: "我需要分析竞品资料，识别用户价值、功能机会、竞争差异和产品优化方向。" },
  { id: "technical_review", name: "评估技术方案", role: "researcher", scenario: "paper", task: "我需要评估这份技术资料的技术路线、核心优势、技术风险和优化方向。" },
  { id: "product_strategy", name: "生成产品策略", role: "product_manager", scenario: "product_document", task: "我需要基于这份产品资料梳理用户痛点、产品机会、功能建议和优先级。" },
];
const TASK_HISTORY_KEY = "ai-insight-agent-task-history";
const ACTIVITY_LOG_KEY = "researchos-activity-log";
const DEMO_KNOWLEDGE_KEY = "researchos-demo-knowledge-initialized";
const DEMO_KNOWLEDGE_ASSETS = [
  { title: "Demo · 低碳胶凝材料技术路线研究", type: "论文资料", status: "Demo资料", detail: "用于展示技术路线、材料性能与研究方向的资料卡。" },
  { title: "Demo · 低碳建筑材料制备工艺专利", type: "专利资料", status: "Demo资料", detail: "用于展示成果规划与专利方向的资料卡。" },
  { title: "Demo · 建筑材料企业合作项目需求", type: "项目资料", status: "Demo资料", detail: "用于展示企业需求分析与项目交付流程。" },
];

function loadTaskHistory() {
  try {
    const saved = JSON.parse(window.localStorage.getItem(TASK_HISTORY_KEY) || "[]");
    return Array.isArray(saved) ? saved.filter((item) => item && typeof item === "object").slice(0, 8) : [];
  } catch {
    return [];
  }
}

function saveTaskHistory(record) {
  const history = [record, ...loadTaskHistory()].slice(0, 8);
  window.localStorage.setItem(TASK_HISTORY_KEY, JSON.stringify(history));
}

function loadActivityLog() {
  try {
    const saved = JSON.parse(window.localStorage.getItem(ACTIVITY_LOG_KEY) || "[]");
    return Array.isArray(saved) ? saved.filter((item) => item && typeof item === "object").slice(0, 30) : [];
  } catch {
    return [];
  }
}

function saveActivityLog(record) {
  const history = [record, ...loadActivityLog()].slice(0, 30);
  window.localStorage.setItem(ACTIVITY_LOG_KEY, JSON.stringify(history));
}
const DEMO_CASES = [
  { name: "新能源汽车技术路线分析", role: "researcher", scenario: "paper", task: "分析新能源汽车技术路线的核心创新、技术风险和后续研究建议。" },
  { name: "竞品产品分析", role: "product_manager", scenario: "product_document", task: "分析这份竞品资料的产品定位、用户价值、功能机会和竞争差异。" },
  { name: "企业解决方案评估", role: "pre_sales_consultant", scenario: "technical_document", task: "分析该企业解决方案的客户需求匹配、核心模块、实施风险和沟通建议。" },
];
const FULL_DEMO_CASE = {
  name: "体验完整案例",
  role: "pre_sales_consultant",
  scenario: "technical_document",
  task: "我要准备一次客户技术交流，需要分析该方案优势、风险并生成沟通策略。",
};
const RESEARCH_REPORT_TASKS = [
  { id: "literature_review", name: "论文综述", description: "研究背景、技术路线、方法比较与未来方向" },
  { id: "technology_roadmap", name: "研究趋势", description: "技术发展路线、阶段与当前挑战" },
  { id: "research_gap", name: "创新点分析", description: "研究空白、潜在方向与验证建议" },
];
const SCENARIO_OPTIONS = [
  {
    id: "paper",
    name: "科研论文分析",
    description: "提炼研究主题、方法、创新点与局限性。",
  },
  {
    id: "technical_document",
    name: "企业技术文档分析",
    description: "梳理技术方案、模块、风险与实施建议。",
  },
  {
    id: "product_document",
    name: "产品资料分析",
    description: "识别产品定位、用户价值、功能与应用场景。",
  },
];
const AGENT_ROLE_LABELS = {
  literature: "科研文献分析师",
  knowledge: "科研知识专家",
  trend: "研究趋势顾问",
  innovation: "创新分析顾问",
  project: "项目方案顾问",
  report: "科研报告顾问",
};
const FDE_SCENARIO_DATA = {
  "高校实验室": {
    background: "实验室需要沉淀分散的论文、实验与项目资料，并缩短企业合作项目的前期准备。",
    problem: "资料理解与技术路线讨论主要依赖人工整理，研究资产难以复用。",
    solution: "以 Research Workspace 组织授权资料，结合知识空间、受控执行和人工审核形成交付流程。",
    mapping: ["科研资料分散", "知识空间 + 文献管理", "Research Workspace / Knowledge Space"],
  },
  "企业研发中心": {
    background: "企业研发团队需要更快核验技术资料、识别合作方向，并保持方案输出可追溯。",
    problem: "技术资料、需求与验证结论之间缺少统一的协作视图。",
    solution: "以企业需求为入口，映射受控分析、Evidence 复核与项目交付材料。",
    mapping: ["技术需求匹配", "受控资料分析 + Evidence", "Research Worker / Evidence Center"],
  },
  "产学研平台": {
    background: "平台需要让高校研究能力、企业需求和合作成果路径在同一流程中可讨论、可复核。",
    problem: "供需信息与项目成果规划存在协作断层，验收口径不易统一。",
    solution: "通过需求映射、项目规划与 Human Review 建立可沟通的协作闭环。",
    mapping: ["供需协同困难", "需求分析 + 项目成果规划", "Research Master / Project Center"],
  },
};

createApp({
  setup() {
    const scenario = ref("paper");
    const role = ref("researcher");
    const task = ref(DEFAULT_TASK);
    const selectedFile = ref(null);
    const fileInput = ref(null);
    const result = ref(null);
    const question = ref("");
    const chatMessages = ref([]);
    const loading = ref(false);
    const asking = ref(false);
    const errorMessage = ref("");
    const activeWorkspaceView = ref("dashboard");
    const connectionState = ref("CONNECTING");
    const connectionMessage = ref("Connecting workspace");
    const sessionToken = ref(window.localStorage.getItem("researchos_session_token") || "");
    // Invalidates a stale identity restore when a user starts a new session while
    // the application is still checking a previously stored token.
    let identityRequestEpoch = 0;
    const identityProfile = ref(null);
    const identityMenuOpen = ref(false);
    const identityRestoreError = ref("");
    const authMode = ref("login");
    const loginForm = ref({ email: "", password: "" });
    const registrationForm = ref({ name: "", email: "", password: "", workspace_name: "" });
    const loginLoading = ref(false);
    const demoLoading = ref(false);
    const loginError = ref("");
    const currentUser = computed(() => identityProfile.value?.user || null);
    const currentWorkspace = computed(() => identityProfile.value?.workspace || null);
    const currentRole = computed(() => identityProfile.value?.workspace?.role || null);
    const aiWorkerCapabilities = ref(null);
    const workspaceContext = ref(null);
    const workspaceContextLoading = ref(false);
    const workspaceContextError = ref("");
    const researchMemory = ref([]);
    const selectedResearchMemory = ref(null);
    const researchMemoryActionError = ref("");
    const assistantPanelOpen = ref(false);
    const assistantDraft = ref("");
    const libraryPapers = ref([]);
    const librarySearch = ref("");
    const libraryStatusFilter = ref("all");
    const libraryLoading = ref(false);
    const libraryUploading = ref(false);
    const libraryAnalysisLoading = ref(false);
    const libraryError = ref("");
    const selectedLibraryPaper = ref(null);
    const libraryPaperDetail = ref(null);
    const libraryFileInput = ref(null);
    const libraryDocumentType = ref("paper");
    const analysisFromLibrary = ref(false);
    const researchOverview = ref(null);
    const overviewLoading = ref(false);
    const reportRecords = ref([]);
    const reportsLoading = ref(false);
    const reportsError = ref("");
    const selectedReport = ref(null);
    const reportDetailLoading = ref(false);
    const ragQuestion = ref("");
    const ragAnswer = ref("");
    const ragSources = ref([]);
    const ragConfidence = ref("");
    const ragLoading = ref(false);
    const ragError = ref("");
    const ragSelectedPaperIds = ref([]);
    const ragAgentPlan = ref(null);
    const ragAgentTrace = ref(null);
    const ragRetrievalEvaluation = ref(null);
    const ragSourceQuality = ref(null);
    const ragConflictReport = ref(null);
    const ragHistory = ref([]);
    const ragHistoryLoading = ref(false);
    const ragSelectedSource = ref(null);
    const ragReportType = ref("literature_review");
    const ragReportResult = ref(null);
    const ragReportSources = ref([]);
    const ragReportQuality = ref(null);
    const ragReportTrace = ref(null);
    const ragReportEvaluation = ref(null);
    const ragReportConflictReport = ref(null);
    const ragReportLoading = ref(false);
    const ragReportError = ref("");
    const showSimulation = ref(false);
    const selectedQuickTask = ref("");
    const taskHistory = ref(loadTaskHistory());
    // ResearchOS is a lightweight product layer over the existing paper
    // library and RAG services. Task output is deliberately kept in the
    // current browser session; no new persistence subsystem is introduced.
    const researchOsOverview = ref(null);
    const researchOsAgents = ref([]);
    const researchOsGoal = ref("");
    const researchOsSelectedAgents = ref(["literature", "knowledge", "trend", "innovation", "project", "report"]);
    const researchOsTaskResult = ref(null);
    const researchOsTaskLoading = ref(false);
    const researchOsError = ref("");
    // P12: Workflow Studio orchestrates existing Agent capabilities. A preview
    // is a plan only; it never synthesizes evidence or a research conclusion.
    const workflowPreview = ref(null);
    const workflowLoading = ref(false);
    const workflowError = ref("");
    let workflowPollTimer = null;
    // P3: persistent, evidence-bounded Research Master workspace snapshots.
    const researchWorkspaces = ref([]);
    const selectedResearchWorkspace = ref(null);
    const workspaceQuality = ref(null);
    const workspaceDecisionCandidate = ref(null);
    const workspaceDeliverable = ref(null);
    const workspaceIntelligenceLoading = ref(false);
    const workspaceIntelligenceError = ref("");
    const workspaceDeliverableLoading = ref(false);
    const workspaceMembers = ref([]);
    const workspaceWorkflow = ref(null);
    const workspaceReviews = ref([]);
    const workspaceEvidenceGraph = ref(null);
    const workspaceReviewLoading = ref(false);
    // ResearchOS v3: user-visible execution state only; never model reasoning.
    const autonomousGoal = ref("帮助低碳建筑材料实验室寻找企业合作创新方向，并形成待负责人确认的技术路线与成果规划。");
    const autonomousRun = ref(null);
    const autonomousRuns = ref([]);
    const autonomousTools = ref([]);
    const autonomousMemory = ref(null);
    const autonomousLoading = ref(false);
    const autonomousError = ref("");
    // ResearchOS v4: a separate bounded execution workspace, backed by the
    // Research Worker API rather than the Research Master orchestration API.
    const workerGoal = ref("分析低碳建筑材料实验数据，并生成企业技术合作方案。");
    const workerRun = ref(null);
    const workerTools = ref([]);
    const workerTimeline = ref([]);
    const workerLoading = ref(false);
    const workerError = ref("");
    const workerReviewDecision = ref("");
    const workerReviewNote = ref("");
    // P7: independent, approval-gated execution tasks. These never replace
    // Research Master, Research Worker, or the existing Evidence workflow.
    const operatorGoal = ref("");
    const operatorTask = ref(null);
    const operatorTasks = ref([]);
    const operatorTools = ref([]);
    const operatorLoading = ref(false);
    const operatorError = ref("");
    const computerGoal = ref("");
    const computerTask = ref(null);
    const computerTasks = ref([]);
    const computerTools = ref([]);
    const computerLoading = ref(false);
    const computerPlanLoading = ref(false);
    const computerError = ref("");
    const computerPlanPreview = ref(null);
    const computerMemory = ref(null);
    const computerEnvironment = ref(null);
    const computerProCatalog = ref(null);
    const computerMode = ref("assist");
    const computerAutonomousId = ref("");
    // P21: solution delivery is a reviewable FDE draft. It never represents
    // a confirmed customer engagement and only links existing Evidence.
    const fdeSolutions = ref([]);
    const selectedFdeSolution = ref(null);
    const fdeSolutionForm = ref({ title: "", customer_need: "", industry: "Higher Education", objective: "" });
    const fdeSolutionAnalysis = ref(null);
    const fdeSolutionBlueprint = ref(null);
    const fdeSolutionPackage = ref(null);
    const fdeComputerMissions = ref([]);
    const fdeSolutionLoading = ref(false);
    const fdeSolutionError = ref("");
    const fdeSolutionReviewNote = ref("");
    const fdeSolutionVersions = ref([]);
    // P22 Mission Center uses only persisted, user-readable lifecycle events.
    const aiMissions = ref([]);
    const selectedAIMission = ref(null);
    const aiMissionDashboard = ref(null);
    const aiMissionForm = ref({ title: "", mission_type: "RESEARCH", goal: "" });
    const aiMissionLoading = ref(false);
    const aiMissionError = ref("");
    const aiNotifications = ref([]);
    const aiMissionReviewComment = ref("");
    const aiMissionRevisionSummary = ref("");
    const aiMissionDelivery = ref(null);
    const entryCopilotSession = ref(null);
    const entryCopilotResult = ref(null);
    const entryCopilotLoading = ref(false);
    const enterpriseFiles = ref([]);
    const selectedEnterpriseFile = ref(null);
    const enterpriseFileLoading = ref(false);
    const enterpriseFileError = ref("");
    const documentAnalytics = ref(null);
    const adaptiveMissionLoading = ref(false);
    // P30: generated files remain reviewable drafts until a human approves them.
    const missionArtifacts = ref([]);
    const selectedArtifact = ref(null);
    const artifactLoading = ref(false);
    const artifactError = ref("");
    const artifactAnalytics = ref(null);
    // P31 exposes registered connector metadata only; credentials are never entered or displayed here.
    const connectors = ref([]);
    const connectorAnalytics = ref(null);
    const connectorLoading = ref(false);
    const connectorError = ref("");
    const connectorForm = ref({ name: "", sqlite_path: "" });
    const collaborationAnalytics = ref(null);
    const governance = ref({ organizations: [], workspaces: [], logs: [] });
    // P56 records are resolved by the active identity Session. The browser
    // never supplies a user or Workspace id as an authorization signal.
    const approvalRequests = ref([]);
    const approvalLoading = ref(false);
    const approvalError = ref("");
    const computerMissionTask = ref("");
    const computerMissionLoading = ref(false);
    const onboardingState = ref(null);
    const onboardingOpen = ref(false);
    const artifactGallery = ref([]);
    const productDemos = ref([]);
    const copilotInsight = ref(null);
    const copilotActions = ref([]);
    const copilotMemory = ref(null);
    const copilotLoading = ref(false);
    const copilotError = ref("");
    // v4.2 enterprise workspace layer: display roles only, no login/authorization.
    const workspaces = ref([]);
    const activeResearchWorkspace = ref(null);
    const workspaceName = ref("低碳建筑材料科研协作空间");
    const workspaceLoading = ref(false);
    const workspaceError = ref("");
    const researchTasks = ref([]);
    const taskName = ref("");
    const taskType = ref("企业需求分析");
    const pendingTaskProject = ref(null);
    const taskCenterLoading = ref(false);
    const agentMonitor = ref(null);
    const deliveryPreview = ref(null);
    const deliveryLoading = ref(false);
    // v4.3: scenario-only FDE implementation rehearsal. It never changes customer data.
    const fdeStageIndex = ref(0);
    const fdeTaskStatuses = ref(["待开始", "待开始", "待开始", "待开始", "待开始"]);
    const fdeAcceptanceReady = ref(false);
    // v4.4: a presentation-only five-minute FDE solution walkthrough.
    const fdeDemoStep = ref(0);
    const fdeArchitectureSelection = ref("Research Master");
    const fdeArchitectureDescriptions = {
      "用户需求": "把企业目标、资料现状和协作痛点转成可讨论的实施输入。",
      "Research Master": "负责已有多 Agent 工作流的任务理解与编排；本演示不会实际运行模型。",
      "Research Worker": "负责受控文件理解、工具执行摘要和待人工复核交付物。",
      "Tools": "File、Knowledge、Data、Document 等已有受控工具，不执行任意系统操作。",
      "RAG知识库": "仅检索用户上传并完成索引的资料。",
      "Evidence": "提供章节级资料提示；资料不足时明确显示暂无可验证资料。",
      "Human Review": "由负责人审核建议，不会自动替代科研或项目决策。",
      "交付报告": "形成 AI辅助生成、需人工审核的沟通与实施材料。",
    };
    // v5.0: presentation-only FDE solution configuration and diagnosis.
    const fdeClientType = ref("高校实验室");
    const fdeSelectedNeeds = ref(["知识库建设", "文献管理"]);
    const fdeConfigurationResult = ref(null);
    const fdeProblemInput = ref("");
    const fdeDiagnosisResult = ref(null);
    // v5.0 final FDE presentation: scenario reports are client-facing
    // demonstration artifacts only. They never alter tenant configuration.
    const fdeDeliveryScenario = ref("高校实验室");
    const fdeDeliveryReport = ref(null);
    const fdeScenarioOptions = Object.keys(FDE_SCENARIO_DATA);
    const fdeScenarioProfile = computed(() => FDE_SCENARIO_DATA[fdeDeliveryScenario.value] || FDE_SCENARIO_DATA["高校实验室"]);
    // P5 is a read-only solution-delivery layer. It surfaces real local
    // counters and fixed proposal templates without creating customer data.
    const solutionScenarios = ref([]);
    const selectedSolutionScenario = ref("university_lab_management");
    const solutionBlueprint = ref(null);
    const solutionRoi = ref(null);
    const solutionAdminOverview = ref(null);
    const solutionDeliveryReport = ref(null);
    const solutionDemoFlow = ref(null);
    const solutionLoading = ref(false);
    const solutionError = ref("");
    const solutionDemoStep = ref(0);
    // P11.5: organization collaboration is opt-in. No default organization,
    // project, activity or knowledge access entry is fabricated in the UI.
    const enterpriseOrganization = ref(null);
    const enterpriseMembers = ref([]);
    const enterpriseProjects = ref([]);
    const enterpriseActivity = ref([]);
    const enterpriseDashboard = ref(null);
    const enterpriseKnowledge = ref([]);
    const enterpriseLoading = ref(false);
    const enterpriseError = ref("");
    const enterpriseOrgName = ref("");
    const enterpriseAdminName = ref("");
    const enterpriseProjectName = ref("");
    const enterpriseProjectGoal = ref("");
    const enterpriseMeetingNotes = ref("");
    const enterpriseMeeting = ref(null);
    const enterpriseDeliveryPackage = ref(null);
    const researchCommandPlan = computed(() => {
      const goal = researchOsGoal.value.trim() || "定义一个研究目标";
      const readyPapers = researchOsOverview.value?.ready_paper_count ?? readyPaperCount.value;
      const knowledgeStatus = readyPapers > 0
        ? `当前知识空间中有 ${readyPapers} 份可检索资料，将作为可引用范围。`
        : "Knowledge base currently contains insufficient evidence. 请先上传并索引研究资料。";
      return {
        goal,
        scope: "当前 Research Workspace 中已授权、已解析并可检索的研究资料。",
        knowledgeStatus,
        steps: ["理解研究目标与范围", "检索相关知识与 Evidence", "分析研究路径、风险与空白", "形成待人工确认的研究建议"],
        tools: readyPapers > 0 ? ["Knowledge Retrieval", "Evidence Center", "Research Master"] : ["Knowledge Space", "Research Master"],
        expected: readyPapers > 0 ? "证据支持的研究结论、风险提示与下一步建议。" : "资料不足说明与上传资料建议；不会生成无依据科研结论。",
      };
    });
    const implementationRisks = computed(() => [
      { name: "数据质量风险", reason: "资料可能缺少必要字段、可提取文本或明确授权范围。", impact: "知识检索与交付内容只能提示资料不足，不能据此形成科研结论。", recommendation: "先核验资料来源、完整性与授权范围，再建立知识空间。" },
      { name: "AI可信风险", reason: "输出可能缺少可验证 Evidence，或检索资料覆盖不足。", impact: "建议不能作为已验证的技术或科研事实。", recommendation: "要求展示 Evidence，并由负责人通过 Human Review 确认。" },
      { name: "用户使用风险", reason: "客户未明确任务目标、验收口径或角色分工。", impact: "实施范围可能扩大，交付预期可能不一致。", recommendation: "在需求调研阶段确认目标、职责、资料边界和验收标准。" },
      { name: "项目实施风险", reason: "真实客户资料接入、索引状态和培训节奏可能不一致。", impact: "上线验证可能延期，需分阶段推进。", recommendation: "采用小范围授权资料试运行，并以受控任务和客户验收逐步扩展。" },
    ]);
    const researchBi = ref(null);
    const researchBiLoading = ref(false);
    const researchProjects = ref([]);
    const projectLoading = ref(false);
    const projectError = ref("");
    const projectMatching = ref(false);
    const projectMatchResult = ref(null);
    const projectForm = ref({ name: "", enterprise_requirement: "", research_goal: "", technology_route: "", paper_plan: "", patent_plan: "", outcome_management: "", status: "planning" });
    // Set only after a human has adopted an action. The user still reviews and
    // explicitly submits the project form; ResearchOS never creates projects autonomously.
    const pendingProjectActionId = ref("");
    // Research decision loop: actions are created only from visible Agent output.
    const researchActions = ref([]);
    const researchDecisions = ref([]);
    const actionLoading = ref(false);
    const actionError = ref("");
    const decisionNotes = ref({});
    const selectedOutcomeProjectId = ref("");
    const projectOutcomes = ref([]);
    const outcomeLoading = ref(false);
    const outcomeError = ref("");
    const outcomeForm = ref({ outcome_type: "论文", title: "", status: "规划中", description: "", source_action_id: "" });
    const valueAssessment = ref(null);
    const valueAssessmentLoading = ref(false);
    const labProfile = ref(null);
    const labProfileLoading = ref(false);
    const evidenceItems = ref([]);
    const evidenceLoading = ref(false);
    const evidenceError = ref("");
    const systemStatus = ref(null);
    const systemStatusLoading = ref(false);
    const systemStatusError = ref("");
    const runtimeStatus = ref(null);
    const runtimeStatusLoading = ref(false);
    const llmRuntimeStatus = ref(null);
    const benchmarkTasks = ref([]);
    const benchmarkDashboard = ref(null);
    const enterpriseScenarios = ref([]);
    const scenarioRunResult = ref(null);
    const scenarioLoading = ref(false);
    const workspaceExperience = ref(null);
    const workspaceExperienceError = ref("");
    const knowledgeMemory = ref({ assets: [], decisions: [], dashboard: null });
    const productShowcase = ref({ overview: null, workflow: null, capabilities: null, releases: null, business: null });
    const workflowDiagnostics = ref(null);
    const agentAnalytics = ref([]);
    const adaptiveAnalytics = ref(null);
    const copilotAnalytics = ref(null);
    const agentMemories = ref([]);
    const diagnosticsLoading = ref(false);
    const diagnosticsError = ref("");
    const activityLogs = ref(loadActivityLog());
    const demoKnowledgeInitialized = ref(window.localStorage.getItem(DEMO_KNOWLEDGE_KEY) === "true");
    const advisorAudience = ref("enterprise_partner");
    const advisorRoles = [
      { id: "mentor", name: "导师", description: "关注研究方向、创新价值与成果路径。" },
      { id: "student", name: "学生", description: "关注学习资料、研究任务与下一步实验。" },
      { id: "research_admin", name: "科研管理员", description: "关注科研资产、项目状态与成果沉淀。" },
      { id: "enterprise_partner", name: "企业合作方", description: "关注需求匹配、技术路线与预期交付。" },
    ];
    const demoStarted = ref(false);
    const demoSteps = [
      { id: "need", title: "企业需求输入", detail: "开发低碳建筑材料，兼顾工程适用性与科研成果。", view: "projects" },
      { id: "master", title: "Research Master 任务拆解", detail: "分配知识检索、趋势、创新、项目规划与报告任务。", view: "tasks" },
      { id: "timeline", title: "Agent Timeline 展示协作", detail: "以用户可理解的摘要展示各专项 Agent 的执行状态和输出。", view: "timeline" },
      { id: "match", title: "实验室能力匹配", detail: "Project Agent 基于团队资料输出能力匹配与风险。", view: "projects" },
      { id: "evidence", title: "Evidence Center 复核依据", detail: "展示来源文件、资料类型、章节片段与关联 Agent。", view: "evidence" },
      { id: "route", title: "技术路线与创新机会", detail: "基于检索证据生成技术建议与创新辅助判断。", view: "tasks" },
      { id: "delivery", title: "项目规划与交付中心", detail: "组织技术路线、论文专利规划和阶段性交付物。", view: "delivery" },
      { id: "outcome", title: "FDE 解决方案报告", detail: "汇总客户需求、能力匹配、分析依据与成果规划。", view: "fde-report" },
      { id: "value", title: "客户价值总结", detail: "说明企业、实验室和高校在协同交付中的价值。", view: "customer-value" },
    ];

    const selectedScenario = computed(() => (
      SCENARIO_OPTIONS.find((item) => item.id === scenario.value) || SCENARIO_OPTIONS[0]
    ));
    const selectedRole = computed(() => (
      ROLE_OPTIONS.find((item) => item.id === role.value) || ROLE_OPTIONS[0]
    ));
    const roleHistory = computed(() => taskHistory.value
      .filter((item) => item.role === role.value)
      .slice(0, 3));
    const filteredLibraryPapers = computed(() => {
      const keyword = librarySearch.value.trim().toLowerCase();
      return libraryPapers.value.filter((paper) => {
        const status = paper.quality_status || paper.analysis_status || "";
        const matchesKeyword = !keyword || [paper.title, paper.filename]
          .some((value) => String(value || "").toLowerCase().includes(keyword));
        const matchesStatus = libraryStatusFilter.value === "all"
          || status === libraryStatusFilter.value;
        return matchesKeyword && matchesStatus;
      });
    });
    const knowledgeChunkTotal = computed(() => libraryPapers.value
      .reduce((total, paper) => total + Number(paper.chunk_count || 0), 0));
    const readyPaperCount = computed(() => libraryPapers.value
      .filter((paper) => ["ready", "indexed"].includes(paper.quality_status || paper.analysis_status))
      .length);
    const researchOsSections = computed(() => {
      const report = researchOsTaskResult.value;
      if (!report) return [];
      return [
        ["文献分析", report.literature_analysis],
        ["知识洞察", report.knowledge_insights],
        ["趋势判断", report.trend_insights],
        ["创新机会", report.innovation_opportunities],
        ["项目与成果规划", report.project_plan],
        ["科研决策报告", report.report],
      ].filter(([, value]) => value && typeof value === "object");
    });
    const actionableTaskSuggestions = computed(() => {
      const report = researchOsTaskResult.value;
      if (!report) return [];
      const collect = (value) => Array.isArray(value) ? value : typeof value === "string" ? [value] : [];
      return [
        ["Innovation Agent", report.innovation_opportunities],
        ["Project Agent", report.project_plan],
      ].flatMap(([sourceAgent, payload]) => Object.values(payload || {})
        .flatMap(collect)
        .map((title) => ({ sourceAgent, title: String(title).trim() }))
        .filter((item) => item.title && item.title !== "未执行"))
        .slice(0, 8);
    });
    const agentTimeline = computed(() => {
      if (researchOsTaskResult.value?.master_plan?.workflow_steps?.length) {
        const runByAgent = new Map((researchOsTaskResult.value.agent_runs || [])
          .map((run) => [run.agent, run]));
        return researchOsTaskResult.value.master_plan.workflow_steps.map((step) => {
          const run = runByAgent.get(step.agent);
          return {
            agent: step.agent,
            status: run?.status || "completed",
            action: step.action,
            summary: run?.message || step.purpose,
          };
        });
      }
      if (projectMatchResult.value?.agent_trace?.length) {
        return projectMatchResult.value.agent_trace.map((trace) => ({
          agent: trace.agent,
          status: trace.status || "completed",
          action: "企业需求匹配",
          summary: trace.message,
        }));
      }
      return demoSteps.map((item) => ({
        agent: item.id === "master" ? "Research Master" : "待调度专项 Agent",
        status: "pending",
        action: item.title,
        summary: item.detail,
      }));
    });
    const aiActivityStream = computed(() => {
      const status = researchOsTaskLoading.value ? "working"
        : researchOsTaskResult.value ? "completed" : "ready";
      const label = status === "working" ? "处理中" : status === "completed" ? "已完成" : "待执行";
      const hasAdoptedAction = researchDecisions.value.some((item) => item.decision === "已采纳" || item.decision === "已修改");
      const hasAction = researchActions.value.length > 0;
      return [
        { agent: "AI Worker · Research Skill", action: "理解需求并检索可追溯资料", status, label },
        { agent: "AI Worker · Review Skill", action: "核验 Evidence 与研究边界", status, label },
        { agent: "AI Worker · Delivery Skill", action: "准备待人工复核的交付草稿", status, label },
        { agent: "Human Review", action: hasAdoptedAction ? "建议已确认，进入项目执行" : hasAction ? "AI 建议已生成，等待负责人确认" : "等待形成有依据的行动建议", status: hasAdoptedAction ? "completed" : hasAction ? "working" : "ready", label: hasAdoptedAction ? "已确认" : hasAction ? "待确认" : "待生成" },
      ];
    });
    const agentTeamCards = computed(() => [
      {
        id: "master",
        name: "Research Master",
        name_cn: "科研项目负责人",
        description: "理解科研目标，编排专项 Agent 协作流程，并汇总可复核的决策输出。",
        purpose: "统一任务规划与交付协调",
      },
      ...researchOsAgents.value.map((agent) => ({
        ...agent,
        name_cn: AGENT_ROLE_LABELS[agent.id] || agent.name_cn,
      })),
    ]);
    const aiWorkerSkills = computed(() => aiWorkerCapabilities.value?.skills || []);
    const evidenceCenterItems = computed(() => {
      const currentItems = [];
      const addSources = (sources, relatedAgent, basis) => {
        (Array.isArray(sources) ? sources : []).forEach((source) => {
          if (!source || typeof source !== "object") return;
          currentItems.push({
            paper_id: source.paper_id || "",
            source_file: source.filename || source.paper_title || "未命名资料",
            paper_title: source.paper_title || "未命名资料",
            document_type: source.document_type || "paper",
            section: source.section || "正文",
            content: source.content || "暂无可展示片段。",
            related_agent: relatedAgent,
            basis,
            score: source.score,
          });
        });
      };
      addSources(researchOsTaskResult.value?.sources, "Research Master / 专项 Agent", "科研任务分析依据");
      addSources(projectMatchResult.value?.sources, "Project Agent", "企业需求匹配依据");
      addSources(labProfile.value?.sources, "Knowledge Agent", "实验室能力画像依据");
      const combined = [...currentItems, ...evidenceItems.value];
      const seen = new Set();
      return combined.filter((item) => {
        const key = `${item.paper_id}-${item.section}-${item.related_agent}`;
        if (seen.has(key)) return false;
        seen.add(key);
        return true;
      });
    });
    const visibleDemoKnowledgeAssets = computed(() => (
      demoKnowledgeInitialized.value ? DEMO_KNOWLEDGE_ASSETS : []
    ));

    const fileSizeLabel = computed(() => {
      if (!selectedFile.value) return "";
      const sizeInMb = selectedFile.value.size / 1024 / 1024;
      return sizeInMb >= 1
        ? `${sizeInMb.toFixed(1)} MB`
        : `${Math.max(1, Math.round(selectedFile.value.size / 1024))} KB`;
    });

    const uploadStatus = computed(() => {
      if (loading.value) return "正在分析";
      if (selectedFile.value) return "文件已就绪";
      return "等待上传";
    });

    const analysisData = computed(() => result.value?.analysis || result.value?.result || {});

    const decisionReport = computed(() => {
      const report = result.value?.decision_report;
      if (!report || typeof report !== "object" || Array.isArray(report)) return null;
      const normalized = {
        summary: typeof report.summary === "string" ? report.summary : "",
        keyPoints: Array.isArray(report.key_points) ? report.key_points : [],
        risks: Array.isArray(report.risks) ? report.risks : [],
        recommendations: Array.isArray(report.recommendations) ? report.recommendations : [],
        businessValue: typeof report.business_value === "string" ? report.business_value : "",
      };
      if (!normalized.summary && !normalized.keyPoints.length && !normalized.risks.length
        && !normalized.recommendations.length && !normalized.businessValue) {
        return null;
      }
      return normalized;
    });

    const businessReport = computed(() => {
      const report = result.value?.business_report;
      if (!report || typeof report !== "object" || Array.isArray(report)) return null;
      const normalized = {
        decisionSummary: typeof report.decision_summary === "string" ? report.decision_summary : "",
        importantFindings: Array.isArray(report.important_findings) ? report.important_findings : [],
        businessOpportunities: Array.isArray(report.business_opportunities) ? report.business_opportunities : [],
        risks: Array.isArray(report.risks) ? report.risks : [],
        recommendedActions: Array.isArray(report.recommended_actions) ? report.recommended_actions : [],
        expectedValue: typeof report.expected_value === "string" ? report.expected_value : "",
      };
      return Object.values(normalized).some((value) => (Array.isArray(value) ? value.length : value))
        ? normalized : null;
    });

    const evidenceSources = computed(() => Array.isArray(result.value?.evidence_sources)
      ? result.value.evidence_sources.filter((item) => item && typeof item === "object") : []);
    const evidenceCards = computed(() => Array.isArray(result.value?.evidence_cards)
      ? result.value.evidence_cards.filter((item) => item && typeof item === "object") : []);
    const trustReport = computed(() => {
      const report = result.value?.trust_report;
      if (!report || typeof report !== "object" || Array.isArray(report)) return null;
      return {
        confidenceScore: Number.isInteger(report.confidence_score) ? report.confidence_score : null,
        informationBasis: Array.isArray(report.information_basis) ? report.information_basis : [],
        uncertainties: Array.isArray(report.uncertainties) ? report.uncertainties : [],
        verificationSuggestions: Array.isArray(report.verification_suggestions) ? report.verification_suggestions : [],
      };
    });
    const valueEstimation = computed(() => {
      const value = result.value?.value_estimation;
      return value && typeof value === "object" && !Array.isArray(value) ? value : null;
    });
    const qualityCheck = computed(() => {
      const check = result.value?.quality_check;
      return check && typeof check === "object" && !Array.isArray(check) ? check : null;
    });
    const agentTrace = computed(() => {
      const trace = result.value?.agent_trace;
      return trace && typeof trace === "object" && !Array.isArray(trace) ? trace : null;
    });
    const agentWorkflow = computed(() => {
      const workflow = result.value?.agent_workflow;
      if (!workflow || typeof workflow !== "object" || Array.isArray(workflow)) return null;
      const steps = Array.isArray(workflow.steps) ? workflow.steps.filter((item) => item && typeof item === "object") : [];
      return steps.length || workflow.planning_summary ? { ...workflow, steps } : null;
    });
    const actionCenter = computed(() => {
      const center = result.value?.action_center;
      if (center && typeof center === "object" && !Array.isArray(center)) return {
        nextActions: Array.isArray(center.next_actions) ? center.next_actions : [],
        questionsToVerify: Array.isArray(center.questions_to_verify) ? center.questions_to_verify : [],
        recommendedTasks: Array.isArray(center.recommended_tasks) ? center.recommended_tasks : [],
      };
      const plan = result.value?.action_plan;
      if (!plan || typeof plan !== "object" || Array.isArray(plan)) return null;
      return {
        nextActions: Array.isArray(plan.immediate_actions) ? plan.immediate_actions : [],
        questionsToVerify: Array.isArray(plan.follow_up_questions) ? plan.follow_up_questions : [],
        recommendedTasks: Array.isArray(plan.recommended_next_steps) ? plan.recommended_next_steps : [],
      };
    });
    const deliverables = computed(() => {
      const source = result.value?.deliverables;
      if (!source || typeof source !== "object" || Array.isArray(source)) return null;
      const entry = Object.entries(source).find(([, value]) => value && typeof value === "object" && !Array.isArray(value));
      if (!entry) return null;
      const labels = {
        customer_communication_plan: "客户沟通方案",
        product_strategy_report: "产品策略报告",
        technical_review_report: "技术评审报告",
      };
      return { title: labels[entry[0]] || "业务产物", entries: Object.entries(entry[1]) };
    });
    const simulationPrompts = computed(() => ({
      researcher: ["关键技术指标如何验证？", "当前方案的实现前提是什么？", "主要技术风险如何缓解？", "下一步需要补充哪些实验或评审材料？", "与替代技术路线相比的边界是什么？"],
      product_manager: ["目标用户最迫切的痛点是什么？", "产品机会需要哪些用户证据支持？", "功能建议的优先级依据是什么？", "竞品差异还需要补充哪些资料？", "下一轮产品评审应确认什么？"],
      pre_sales_consultant: ["该方案如何匹配客户当前业务目标？", "实施依赖和系统集成边界是什么？", "客户最可能关注哪些风险？", "方案优势如何结合客户现状说明？", "下一次客户交流需要确认什么？"],
    }[result.value?.user_role || role.value] || []));

    const analysisEntries = computed(() => Object.entries(analysisData.value)
      .filter(([key]) => key !== "title")
      .map(([key, value]) => ({ key, label: formatResultKey(key), value })));

    const reportTitle = computed(() => {
      const responseScenario = result.value?.scenario;
      if (responseScenario === "paper") return "论文分析结果";
      if (responseScenario === "technical_document") return "技术方案分析";
      if (responseScenario === "product_document") return "产品资料分析";
      return "结构化分析结果";
    });

    const agentDecision = computed(() => {
      if (!result.value) return null;
      const detectedTasks = Array.isArray(result.value.detected_tasks)
        ? result.value.detected_tasks
        : [];
      const executionPlan = Array.isArray(result.value.execution_plan)
        ? result.value.execution_plan
        : [];
      const response = result.value;
      const decision = {
        userRole: typeof response.user_role === "string" ? response.user_role : "",
        roleName: typeof response.role_name === "string" ? response.role_name : "",
        scenario: typeof response.scenario === "string" ? response.scenario : "",
        documentType: typeof response.document_type === "string" ? response.document_type : "",
        userIntent: typeof response.user_intent === "string" ? response.user_intent : "",
        userTask: typeof response.user_task === "string" ? response.user_task : response.task || "",
        detectedTasks,
        decisionReason: typeof response.decision_reason === "string" ? response.decision_reason : "",
        executionPlan,
      };

      if (!Object.values(decision).some((value) => (
        Array.isArray(value) ? value.length : Boolean(value)
      ))) {
        return null;
      }
      return decision;
    });

    function formatResultKey(key) {
      return key.replaceAll("_", " ");
    }

    function selectRole(item) {
      role.value = item.id;
      scenario.value = item.scenario;
      task.value = item.task;
      selectedQuickTask.value = "";
    }

    function selectQuickTask(item) {
      selectedQuickTask.value = item.id;
      role.value = item.role;
      scenario.value = item.scenario;
      task.value = item.task;
      errorMessage.value = "";
    }

    function applyDemo(item) {
      role.value = item.role;
      scenario.value = item.scenario;
      task.value = item.task;
      errorMessage.value = "";
      selectedQuickTask.value = "";
    }

    async function openWorkspaceView(view) {
      if (currentWorkspace.value?.is_demo && ["governance", "system", "benchmarks"].includes(view)) {
        activeWorkspaceView.value = "dashboard";
        errorMessage.value = "Admin Console is not available in the Demo Workspace.";
        return;
      }
      activeWorkspaceView.value = view;
      libraryError.value = "";
      reportsError.value = "";
      if (view === "knowledge") await loadLibraryPapers();
      if (view === "outcomes") await loadResearchReports();
      if (view === "insights") {
        await loadLibraryPapers();
        await loadRagHistory();
      }
      if (view === "dashboard" || view === "tasks" || view === "agents") {
        await loadResearchOsData();
      }
      if (view === "dashboard") await loadWorkspaceExperience();
      if (view === "dashboard" || view === "artifact-center" || view === "demo-center") await loadProductExperience();
      if (view === "workflow-studio") await loadResearchWorkflows();
      if (view === "dashboard") await loadResearchWorkspaces();
      if (view === "dashboard") await loadAIMissions();
      if (view === "research-workspace") await loadResearchWorkspaces();
      if (view === "autonomous") await loadAutonomousWorkspace();
      if (view === "worker") await loadResearchWorkerWorkspace();
      if (view === "operator") await loadOperatorStudio();
      if (view === "computer") await loadComputerStudio();
      if (view === "copilot") await loadCopilotCenter();
      if (view === "document-intelligence") await Promise.all([loadEnterpriseFiles(), loadDocumentAnalytics()]);
      if (view === "workspace" || view === "task-center") await loadEnterpriseWorkspace();
      if (view === "agent-monitor") await loadAgentMonitor();
      if (view === "delivery-center") await loadClientDelivery();
      if (view === "projects") await loadResearchProjects();
      if (view === "outcome-center") {
        await loadResearchProjects();
        await loadResearchActions();
      }
      if (view === "bi") await loadResearchBi();
      if (view === "evidence") await loadEvidenceCenter();
      if (view === "lab-profile") await loadResearchBi();
      if (view === "system") await Promise.all([loadSystemStatus(), loadRuntimeStatus(), loadLlmRuntimeStatus(), loadWorkflowDiagnostics(), loadAgentAnalytics(), loadCopilotAnalytics(), loadDocumentAnalytics(), loadAgentMemories(), loadConnectorCenter(), loadCollaborationAnalytics()]);
      if (view === "connector-center") await loadConnectorCenter();
      if (view === "governance") await loadGovernance();
      if (view === "benchmarks") await loadBenchmarks();
      if (view === "scenario-center") await loadScenarios();
      if (view === "ai-workspace") await Promise.all([loadWorkspaceExperience(), loadUnifiedWorkspaceContext()]);
      if (view === "memory-center") await loadKnowledgeMemory();
      if (["showcase","architecture","capabilities","business-dashboard","release-center"].includes(view)) await loadProductShowcase();
      if (view === "solution-delivery") await loadSolutionDelivery();
      if (view === "fde-solution-studio") await loadFdeSolutions();
      if (view === "mission-center" || view === "team-workspace") await Promise.all([loadAIMissions(), loadApprovalQueue()]);
      if (view === "enterprise-hub") await loadEnterpriseHub();
      void loadResearchOverview();
    }

    async function loadProductExperience() {
      try {
        const [onboardingResponse, artifactsResponse, demosResponse] = await Promise.all([
          fetchWithTimeout(`${API_BASE_URL}/researchos/product/onboarding/local`),
          fetchWithTimeout(`${API_BASE_URL}/researchos/product/artifacts`),
          fetchWithTimeout(`${API_BASE_URL}/researchos/product/demos`),
        ]);
        onboardingState.value = await readResponse(onboardingResponse);
        artifactGallery.value = (await readResponse(artifactsResponse)).artifacts || [];
        productDemos.value = (await readResponse(demosResponse)).demos || [];
        onboardingOpen.value = Boolean(onboardingState.value?.first_visit);
      } catch (_error) {
        // Product metadata must never block the existing research workflow.
      }
    }

    async function completeOnboarding(step) {
      try {
        onboardingState.value = await readResponse(await fetchWithTimeout(`${API_BASE_URL}/researchos/product/onboarding/local/complete`, {
          method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ step }),
        }));
      } catch (_error) {
        // A local welcome layer remains optional when product metadata is unavailable.
      } finally { onboardingOpen.value = false; }
    }

    function startProductDemo(item) {
      if (item.id === "research") {
        beginResearchFromHome("Analyze the indexed research materials and prepare an evidence-backed research workflow.");
      } else if (item.id === "coding") {
        computerGoal.value = "Optimize my frontend";
        computerPlanPreview.value = null;
        activeWorkspaceView.value = "computer";
      } else {
        activeWorkspaceView.value = "solution-delivery";
      }
    }

    async function generateResearchWorkflow(goal = "") {
      const value = (goal || researchOsGoal.value).trim();
      if (!value) { workflowError.value = "请输入研究目标后再生成工作流。"; return; }
      workflowLoading.value = true; workflowError.value = "";
      try {
        const response = await fetchWithTimeout(`${API_BASE_URL}/researchos/workflows`, {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ goal: value, workspace_id: selectedResearchWorkspace.value?.workspace_id || null }),
        });
        workflowPreview.value = await readResponse(response);
        activeWorkspaceView.value = "workflow-studio";
      } catch (error) { workflowError.value = error.message || "工作流生成失败。"; }
      finally { workflowLoading.value = false; }
    }

    async function loadResearchWorkflows() {
      if (workflowPreview.value || workflowLoading.value) return;
      workflowLoading.value = true; workflowError.value = "";
      try {
        const response = await fetchWithTimeout(`${API_BASE_URL}/researchos/workflows`, { method: "GET" });
        const items = await readResponse(response);
        workflowPreview.value = items[0] || null;
      } catch (error) { workflowError.value = error.message || "工作流读取失败。"; }
      finally { workflowLoading.value = false; }
    }

    async function refreshWorkflowRuntime() {
      if (!workflowPreview.value?.id) return;
      try {
        const [workflowResponse, eventsResponse] = await Promise.all([
          fetchWithTimeout(`${API_BASE_URL}/researchos/workflows/${workflowPreview.value.id}`, { method: "GET" }),
          fetchWithTimeout(`${API_BASE_URL}/researchos/workflows/${workflowPreview.value.id}/events`, { method: "GET" }),
        ]);
        workflowPreview.value = { ...(await readResponse(workflowResponse)), events: await readResponse(eventsResponse) };
        if (["COMPLETED", "WAITING_REVIEW", "WAITING_EVIDENCE"].includes(workflowPreview.value.status) && workflowPollTimer) {
          window.clearInterval(workflowPollTimer); workflowPollTimer = null;
        }
      } catch (_) { /* retain the current runtime state; the next user refresh can retry. */ }
    }

    async function executeResearchWorkflow() {
      if (!workflowPreview.value || workflowLoading.value) return;
      workflowLoading.value = true; workflowError.value = "";
      if (workflowPollTimer) window.clearInterval(workflowPollTimer);
      workflowPollTimer = window.setInterval(() => { void refreshWorkflowRuntime(); }, 900);
      try {
        const response = await fetchWithTimeout(`${API_BASE_URL}/researchos/workflows/${workflowPreview.value.id}/execute`, {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ goal: workflowPreview.value.goal, paper_ids: ragSelectedPaperIds.value || [] }),
        });
        workflowPreview.value = await readResponse(response);
        if (workflowPreview.value.research_workspace?.workspace_id) {
          selectedResearchWorkspace.value = workflowPreview.value.research_workspace;
        }
      } catch (error) { workflowError.value = error.message || "工作流执行失败。"; }
      finally { workflowLoading.value = false; await refreshWorkflowRuntime(); }
    }

    function enterpriseMemberId() {
      return enterpriseOrganization.value?.admin_member_id || enterpriseMembers.value.find((item) => item.role === "Admin")?.id || "";
    }

    async function createEnterpriseOrganization() {
      const name = enterpriseOrgName.value.trim();
      const adminName = enterpriseAdminName.value.trim();
      if (!name || !adminName) {
        enterpriseError.value = "请输入 Organization 名称和管理员显示名。";
        return;
      }
      enterpriseLoading.value = true; enterpriseError.value = "";
      try {
        const response = await fetchWithTimeout(`${API_BASE_URL}/researchos/organizations`, {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ name, admin_name: adminName }),
        });
        enterpriseOrganization.value = await readResponse(response);
        enterpriseLoading.value = false;
        await loadEnterpriseHub();
      } catch (error) { enterpriseError.value = error.message || "Organization 创建失败。"; }
      finally { enterpriseLoading.value = false; }
    }

    async function loadEnterpriseHub() {
      const organizationId = enterpriseOrganization.value?.id;
      if (!organizationId || enterpriseLoading.value) return;
      enterpriseLoading.value = true; enterpriseError.value = "";
      try {
        const memberId = enterpriseMemberId();
        const [membersResponse, projectsResponse, activityResponse, dashboardResponse, knowledgeResponse] = await Promise.all([
          fetchWithTimeout(`${API_BASE_URL}/researchos/organizations/${organizationId}/members`, { method: "GET" }),
          fetchWithTimeout(`${API_BASE_URL}/researchos/organizations/${organizationId}/projects`, { method: "GET" }),
          fetchWithTimeout(`${API_BASE_URL}/researchos/organizations/${organizationId}/activity`, { method: "GET" }),
          fetchWithTimeout(`${API_BASE_URL}/researchos/organizations/${organizationId}/dashboard?member_id=${encodeURIComponent(memberId)}`, { method: "GET" }),
          fetchWithTimeout(`${API_BASE_URL}/researchos/organizations/${organizationId}/knowledge?member_id=${encodeURIComponent(memberId)}`, { method: "GET" }),
        ]);
        enterpriseMembers.value = await readResponse(membersResponse);
        enterpriseProjects.value = await readResponse(projectsResponse);
        enterpriseActivity.value = await readResponse(activityResponse);
        enterpriseDashboard.value = await readResponse(dashboardResponse);
        enterpriseKnowledge.value = await readResponse(knowledgeResponse);
      } catch (error) { enterpriseError.value = error.message || "企业协作数据读取失败。"; }
      finally { enterpriseLoading.value = false; }
    }

    async function createEnterpriseProject() {
      if (!enterpriseOrganization.value || !enterpriseProjectName.value.trim()) return;
      enterpriseLoading.value = true; enterpriseError.value = "";
      try {
        const response = await fetchWithTimeout(`${API_BASE_URL}/researchos/organizations/${enterpriseOrganization.value.id}/projects`, {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ name: enterpriseProjectName.value.trim(), research_goal: enterpriseProjectGoal.value.trim(), owner_member_id: enterpriseMemberId() }),
        });
        await readResponse(response); enterpriseProjectName.value = ""; enterpriseProjectGoal.value = "";
        await loadEnterpriseHub();
      } catch (error) { enterpriseError.value = error.message || "企业项目创建失败。"; }
      finally { enterpriseLoading.value = false; }
    }

    async function createEnterpriseMeeting() {
      if (!enterpriseOrganization.value || !enterpriseMeetingNotes.value.trim()) return;
      enterpriseLoading.value = true; enterpriseError.value = "";
      try {
        const response = await fetchWithTimeout(`${API_BASE_URL}/researchos/organizations/${enterpriseOrganization.value.id}/meetings`, {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ member_id: enterpriseMemberId(), notes: enterpriseMeetingNotes.value.trim() }),
        });
        enterpriseMeeting.value = await readResponse(response); enterpriseMeetingNotes.value = "";
        await loadEnterpriseHub();
      } catch (error) { enterpriseError.value = error.message || "会议提案生成失败。"; }
      finally { enterpriseLoading.value = false; }
    }

    async function loadEnterpriseDeliveryPackage() {
      if (!enterpriseOrganization.value) return;
      enterpriseLoading.value = true; enterpriseError.value = "";
      try {
        const response = await fetchWithTimeout(`${API_BASE_URL}/researchos/organizations/${enterpriseOrganization.value.id}/delivery-package?member_id=${encodeURIComponent(enterpriseMemberId())}`, { method: "GET" });
        enterpriseDeliveryPackage.value = await readResponse(response);
      } catch (error) { enterpriseError.value = error.message || "企业交付包读取失败。"; }
      finally { enterpriseLoading.value = false; }
    }

    async function loadSolutionDelivery() {
      if (solutionLoading.value) return;
      solutionLoading.value = true;
      solutionError.value = "";
      try {
        const [scenariosResponse, roiResponse, overviewResponse] = await Promise.all([
          fetchWithTimeout(`${API_BASE_URL}/researchos/solution-scenarios`, { method: "GET" }),
          fetchWithTimeout(`${API_BASE_URL}/researchos/solution-roi`, { method: "GET" }),
          fetchWithTimeout(`${API_BASE_URL}/researchos/solution-admin-overview`, { method: "GET" }),
        ]);
        solutionScenarios.value = await readResponse(scenariosResponse);
        solutionRoi.value = await readResponse(roiResponse);
        solutionAdminOverview.value = await readResponse(overviewResponse);
        const available = solutionScenarios.value.some((item) => item.scenario_id === selectedSolutionScenario.value);
        if (!available && solutionScenarios.value.length) selectedSolutionScenario.value = solutionScenarios.value[0].scenario_id;
        if (selectedSolutionScenario.value) await selectSolutionScenario(selectedSolutionScenario.value, false);
      } catch (error) {
        solutionError.value = error.message || "解决方案交付层暂时无法加载。";
      } finally {
        solutionLoading.value = false;
      }
    }

    async function selectSolutionScenario(scenarioId, refresh = true) {
      if (!scenarioId) return;
      selectedSolutionScenario.value = scenarioId;
      solutionError.value = "";
      try {
        const [blueprintResponse, reportResponse, demoFlowResponse] = await Promise.all([
          fetchWithTimeout(`${API_BASE_URL}/researchos/solution-scenarios/${scenarioId}/blueprint`, { method: "GET" }),
          fetchWithTimeout(`${API_BASE_URL}/researchos/solution-scenarios/${scenarioId}/delivery-report`, { method: "GET" }),
          fetchWithTimeout(`${API_BASE_URL}/researchos/solution-scenarios/${scenarioId}/demo-flow`, { method: "GET" }),
        ]);
        solutionBlueprint.value = await readResponse(blueprintResponse);
        solutionDeliveryReport.value = await readResponse(reportResponse);
        solutionDemoFlow.value = await readResponse(demoFlowResponse);
        if (refresh) recordActivity("P5客户场景已切换", "仅切换方案模板与真实运行概览，不写入客户数据。");
      } catch (error) {
        solutionError.value = error.message || "客户方案模板暂时无法读取。";
      }
    }

    function startSolutionDemo() {
      selectedSolutionScenario.value = "enterprise_rd_research";
      researchOsGoal.value = "[Demo案例] 分析 RAG 技术发展方向，并比较当前资料中的研究条件差异。";
      solutionDemoStep.value = 0;
      activeWorkspaceView.value = "solution-delivery";
      void loadSolutionDelivery();
      recordActivity("P5解决方案演示已启动", "Demo 只预填研究目标；真实 Evidence 与 Review 状态仍来自当前运行数据。");
    }

    async function loadFdeSolutions() {
      if (fdeSolutionLoading.value) return;
      fdeSolutionLoading.value = true; fdeSolutionError.value = "";
      try {
        const response = await fetchWithTimeout(`${API_BASE_URL}/researchos/solutions`, { method: "GET" });
        fdeSolutions.value = await readResponse(response);
        if (selectedFdeSolution.value?.id) await loadFdeSolutionDetail(selectedFdeSolution.value.id);
      } catch (error) { fdeSolutionError.value = error.message || "解决方案项目暂时无法读取。"; }
      finally { fdeSolutionLoading.value = false; }
    }

    async function loadAIMissions() {
      if (!identityProfile.value?.workspace?.id) return;
      if (aiMissionLoading.value) return;
      aiMissionLoading.value = true; aiMissionError.value = "";
      try {
        const [missionsResponse, dashboardResponse, notificationResponse] = await Promise.all([
          fetchWithTimeout(`${API_BASE_URL}/api/missions`),
          fetchWithTimeout(`${API_BASE_URL}/api/missions/dashboard`),
          fetchWithTimeout(`${API_BASE_URL}/api/notifications`),
        ]);
        aiMissions.value = await readResponse(missionsResponse);
        aiMissionDashboard.value = await readResponse(dashboardResponse);
        aiNotifications.value = await readResponse(notificationResponse);
        if (selectedAIMission.value?.id) await loadAIMissionDetail(selectedAIMission.value.id);
      } catch (error) { aiMissionError.value = error.message || "AI Mission 暂时无法读取。"; }
      finally { aiMissionLoading.value = false; }
    }

    async function loadAIMissionDetail(missionId) {
      if (!missionId) return;
      const response = await fetchWithTimeout(`${API_BASE_URL}/api/missions/${missionId}`);
      selectedAIMission.value = await readResponse(response);
      try {
        selectedAIMission.value.worker_contract = await readResponse(
          await fetchWithTimeout(`${API_BASE_URL}/researchos/ai-worker/missions/${missionId}/contract`),
        );
      } catch (_) { selectedAIMission.value.worker_contract = null; }
      try {
        selectedAIMission.value.worker_runtime = await readResponse(
          await fetchWithTimeout(`${API_BASE_URL}/api/runtime/missions/${missionId}`),
        );
      } catch (_) { selectedAIMission.value.worker_runtime = null; }
      try {
        selectedAIMission.value.workspace_context = await readResponse(
          await fetchWithTimeout(`${API_BASE_URL}/api/missions/${missionId}/context`),
        );
      } catch (_) { selectedAIMission.value.workspace_context = null; }
      try {
        selectedAIMission.value.activity_timeline = await readResponse(
          await fetchWithTimeout(`${API_BASE_URL}/api/missions/${missionId}/activity`),
        );
      } catch (_) { selectedAIMission.value.activity_timeline = null; }
      try {
        selectedAIMission.value.control = await readResponse(
          await fetchWithTimeout(`${API_BASE_URL}/api/missions/${missionId}/control`),
        );
      } catch (_) { selectedAIMission.value.control = null; }
      try { selectedAIMission.value.evaluation = await readResponse(await fetchWithTimeout(`${API_BASE_URL}/api/evaluations/${missionId}`)); } catch (_) { selectedAIMission.value.evaluation = null; }
      try { selectedAIMission.value.agent_traces = await readResponse(await fetchWithTimeout(`${API_BASE_URL}/api/agent-traces/${missionId}`)); } catch (_) { selectedAIMission.value.agent_traces = []; }
      try { selectedAIMission.value.planner_plan = await readResponse(await fetchWithTimeout(`${API_BASE_URL}/api/missions/${missionId}/plan`)); } catch (_) { selectedAIMission.value.planner_plan = null; }
      try { selectedAIMission.value.adaptive_iterations = await readResponse(await fetchWithTimeout(`${API_BASE_URL}/api/missions/${missionId}/iterations`)); selectedAIMission.value.graph_history = await readResponse(await fetchWithTimeout(`${API_BASE_URL}/api/missions/${missionId}/graph-history`)); } catch (_) { selectedAIMission.value.adaptive_iterations = []; selectedAIMission.value.graph_history = []; }
      await loadMissionArtifacts(missionId);
    }

    async function loadMissionArtifacts(missionId = selectedAIMission.value?.id) {
      if (!missionId) { missionArtifacts.value = []; return; }
      try {
        missionArtifacts.value = await readResponse(await fetchWithTimeout(`${API_BASE_URL}/api/missions/${missionId}/artifacts`));
        artifactAnalytics.value = await readResponse(await fetchWithTimeout(`${API_BASE_URL}/api/artifacts/analytics`));
      } catch (error) { artifactError.value = error.message || "Artifact 暂时无法读取。"; }
    }

    async function loadApprovalQueue() {
      approvalLoading.value = true; approvalError.value = "";
      try {
        approvalRequests.value = await readResponse(await fetchWithTimeout(`${API_BASE_URL}/api/approvals`));
      } catch (error) {
        approvalRequests.value = [];
        approvalError.value = error.message || "Review Queue 暂时无法读取。";
      } finally { approvalLoading.value = false; }
    }

    async function resolveApproval(request, action) {
      if (!request?.id) return;
      approvalLoading.value = true; approvalError.value = "";
      try {
        await readResponse(await fetchWithTimeout(`${API_BASE_URL}/api/approvals/${request.id}/${action}`, {
          method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ comment: "Reviewed in Workspace Review Queue." }),
        }));
        await loadApprovalQueue();
      } catch (error) { approvalError.value = error.message || "Review decision 暂时无法提交。"; }
      finally { approvalLoading.value = false; }
    }

    async function loadConnectorCenter() {
      connectorLoading.value = true; connectorError.value = "";
      try {
        const [items, analytics] = await Promise.all([
          readResponse(await fetchWithTimeout(`${API_BASE_URL}/api/connectors`)),
          readResponse(await fetchWithTimeout(`${API_BASE_URL}/api/connectors/analytics`)),
        ]);
        connectors.value = items; connectorAnalytics.value = analytics;
      } catch (error) { connectorError.value = error.message || "Connector Center 暂时无法读取。"; }
      finally { connectorLoading.value = false; }
    }

    async function registerSqliteConnector() {
      if (!connectorForm.value.name || !connectorForm.value.sqlite_path) { connectorError.value = "请输入名称和现有 SQLite 文件路径。"; return; }
      connectorLoading.value = true; connectorError.value = "";
      try {
        await readResponse(await fetchWithTimeout(`${API_BASE_URL}/api/connectors/register`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name: connectorForm.value.name, type: "DATABASE", permission: "READ_ONLY", config: { backend: "SQLITE", sqlite_path: connectorForm.value.sqlite_path } }) }));
        connectorForm.value = { name: "", sqlite_path: "" }; await loadConnectorCenter();
      } catch (error) { connectorError.value = error.message || "Connector 注册失败。"; }
      finally { connectorLoading.value = false; }
    }

    async function loadCollaborationAnalytics() {
      try { collaborationAnalytics.value = await readResponse(await fetchWithTimeout(`${API_BASE_URL}/api/agent/collaboration/analytics`)); }
      catch (_) { collaborationAnalytics.value = null; }
    }

    async function loadGovernance() {
      try { const [organizations, workspaces, logs] = await Promise.all([readResponse(await fetchWithTimeout(`${API_BASE_URL}/api/organizations`)), readResponse(await fetchWithTimeout(`${API_BASE_URL}/api/workspaces`)), readResponse(await fetchWithTimeout(`${API_BASE_URL}/api/audit/events`))]); governance.value = { organizations, workspaces, logs }; }
      catch (_) { governance.value = { organizations: [], workspaces: [], logs: [] }; }
    }

    async function loadRuntimeStatus() {
      if (runtimeStatusLoading.value) return;
      runtimeStatusLoading.value = true;
      try { runtimeStatus.value = await readResponse(await fetchWithTimeout(`${API_BASE_URL}/api/runtime/monitor`)); }
      catch (_) { runtimeStatus.value = null; }
      finally { runtimeStatusLoading.value = false; }
    }

    async function loadLlmRuntimeStatus() {
      try { llmRuntimeStatus.value = await readResponse(await fetchWithTimeout(`${API_BASE_URL}/api/llm-runtime/dashboard`)); }
      catch (_) { llmRuntimeStatus.value = null; }
    }

    async function loadBenchmarks() {
      try { const [tasks,dashboard] = await Promise.all([readResponse(await fetchWithTimeout(`${API_BASE_URL}/api/benchmarks`)),readResponse(await fetchWithTimeout(`${API_BASE_URL}/api/benchmark/dashboard`))]); benchmarkTasks.value=tasks; benchmarkDashboard.value=dashboard; }
      catch (_) { benchmarkTasks.value=[]; benchmarkDashboard.value=null; }
    }
    async function loadScenarios() {
      try { enterpriseScenarios.value = await readResponse(await fetchWithTimeout(`${API_BASE_URL}/api/scenarios`)); }
      catch (_) { enterpriseScenarios.value = []; }
    }
    async function runScenario(scenarioId) {
      scenarioLoading.value = true; scenarioRunResult.value = null;
      try { scenarioRunResult.value = await readResponse(await fetchWithTimeout(`${API_BASE_URL}/api/scenarios/run`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ scenario_id: scenarioId }) })); }
      catch (error) { errorMessage.value = error.message || "Scenario run failed."; }
      finally { scenarioLoading.value = false; }
    }
    async function loadWorkspaceExperience() {
      if (!identityProfile.value?.workspace?.id) return;
      try {
        workspaceExperienceError.value = "";
        workspaceExperience.value = await readResponse(await fetchWithTimeout(`${API_BASE_URL}/api/workspace/dashboard`));
      } catch (error) {
        workspaceExperience.value = null;
        workspaceExperienceError.value = error.message || "Workspace temporarily unavailable.";
      }
    }
    async function loadKnowledgeMemory() {
      try { const [assets, decisions, dashboard] = await Promise.all([readResponse(await fetchWithTimeout(`${API_BASE_URL}/api/knowledge/assets`)), readResponse(await fetchWithTimeout(`${API_BASE_URL}/api/knowledge/decisions`)), readResponse(await fetchWithTimeout(`${API_BASE_URL}/api/knowledge/dashboard`))]); knowledgeMemory.value = { assets, decisions, dashboard }; }
      catch (_) { knowledgeMemory.value = { assets: [], decisions: [], dashboard: null }; }
    }
    async function loadProductShowcase() {
      try { const [overview,workflow,capabilities,releases,business] = await Promise.all([readResponse(await fetchWithTimeout(`${API_BASE_URL}/api/demo/overview`)),readResponse(await fetchWithTimeout(`${API_BASE_URL}/api/demo/workflow`)),readResponse(await fetchWithTimeout(`${API_BASE_URL}/api/product/capabilities`)),readResponse(await fetchWithTimeout(`${API_BASE_URL}/api/product/releases`)),readResponse(await fetchWithTimeout(`${API_BASE_URL}/api/business/dashboard`))]); productShowcase.value={overview,workflow,capabilities,releases,business}; }
      catch (_) { productShowcase.value={overview:null,workflow:null,capabilities:null,releases:null,business:null}; }
    }

    async function generateMissionArtifact(artifactType) {
      if (!selectedAIMission.value?.id) return;
      artifactLoading.value = true; artifactError.value = "";
      try {
        selectedArtifact.value = await readResponse(await fetchWithTimeout(`${API_BASE_URL}/api/missions/${selectedAIMission.value.id}/artifacts/generate`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ artifact_type: artifactType }) }));
        await loadMissionArtifacts();
      } catch (error) { artifactError.value = error.message || "Artifact 生成失败。"; }
      finally { artifactLoading.value = false; }
    }

    async function openArtifact(artifactId) {
      try { selectedArtifact.value = await readResponse(await fetchWithTimeout(`${API_BASE_URL}/api/artifacts/${artifactId}`)); }
      catch (error) { artifactError.value = error.message || "Artifact 详情无法读取。"; }
    }

    async function reviewArtifact(status) {
      if (!selectedArtifact.value?.id) return;
      artifactLoading.value = true; artifactError.value = "";
      try {
        selectedArtifact.value = await readResponse(await fetchWithTimeout(`${API_BASE_URL}/api/artifacts/${selectedArtifact.value.id}/review`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ status }) }));
        await loadMissionArtifacts();
      } catch (error) { artifactError.value = error.message || "审核状态无法更新。"; }
      finally { artifactLoading.value = false; }
    }

    async function reviseArtifact() {
      if (!selectedArtifact.value?.id) return;
      artifactLoading.value = true; artifactError.value = "";
      try {
        selectedArtifact.value = await readResponse(await fetchWithTimeout(`${API_BASE_URL}/api/artifacts/${selectedArtifact.value.id}/revise`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ reason: "Human reviewer requested a revision." }) }));
        await loadMissionArtifacts();
      } catch (error) { artifactError.value = error.message || "无法创建修订版本。"; }
      finally { artifactLoading.value = false; }
    }

    async function downloadArtifact() {
      if (!selectedArtifact.value?.id || selectedArtifact.value.status !== "APPROVED") return;
      try {
        const response = await fetchWithTimeout(`${API_BASE_URL}/api/artifacts/${selectedArtifact.value.id}/download`);
        if (!response.ok) await readResponse(response);
        const blob = await response.blob();
        const filename = response.headers.get("content-disposition")?.match(/filename="?([^";]+)"?/i)?.[1] || "researchos-artifact";
        const link = document.createElement("a");
        link.href = URL.createObjectURL(blob); link.download = filename; link.click(); URL.revokeObjectURL(link.href);
      } catch (error) { artifactError.value = error.message || "Artifact download is temporarily unavailable."; }
    }

    async function runAdaptiveMission() {
      if (!selectedAIMission.value?.id) return;
      adaptiveMissionLoading.value = true;
      try { await readResponse(await fetchWithTimeout(`${API_BASE_URL}/api/missions/${selectedAIMission.value.id}/adaptive-run`, { method: "POST" })); await loadAIMissionDetail(selectedAIMission.value.id); }
      catch (error) { aiMissionError.value = error.message || "Adaptive Loop 暂时无法运行。"; }
      finally { adaptiveMissionLoading.value = false; }
    }

    async function reviewAdaptiveMission(status) {
      if (!selectedAIMission.value?.id) return;
      adaptiveMissionLoading.value = true;
      try { await readResponse(await fetchWithTimeout(`${API_BASE_URL}/api/missions/${selectedAIMission.value.id}/adaptive-review`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ status }) })); await loadAIMissionDetail(selectedAIMission.value.id); }
      catch (error) { aiMissionError.value = error.message || "Adaptive Review 暂时无法提交。"; }
      finally { adaptiveMissionLoading.value = false; }
    }

    async function createAIMission() {
      const payload = aiMissionForm.value;
      if (!payload.title.trim()) { aiMissionError.value = "请先填写 Mission 标题。"; return; }
      aiMissionLoading.value = true; aiMissionError.value = "";
      try {
        const response = await fetchWithTimeout(`${API_BASE_URL}/api/missions`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ ...payload, title: payload.title.trim(), goal: payload.goal.trim() }) });
        selectedAIMission.value = await readResponse(response);
        aiMissionForm.value = { title: "", mission_type: "RESEARCH", goal: "" };
        await loadAIMissions();
      } catch (error) { aiMissionError.value = error.message || "Mission 创建失败。"; }
      finally { aiMissionLoading.value = false; }
    }

    async function startCopilotMission() {
      const goal = researchOsGoal.value.trim();
      if (!goal || entryCopilotLoading.value) return;
      entryCopilotLoading.value = true;
      try {
        const session = await readResponse(await fetchWithTimeout(`${API_BASE_URL}/api/copilot/session`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({}) }));
        const understanding = await readResponse(await fetchWithTimeout(`${API_BASE_URL}/api/copilot/chat`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ session_id: session.id, message: goal }) }));
        const started = await readResponse(await fetchWithTimeout(`${API_BASE_URL}/api/copilot/session/${session.id}/start`, { method: "POST" }));
        entryCopilotSession.value = session; entryCopilotResult.value = { ...understanding, ...started };
        selectedAIMission.value = started.mission; activeWorkspaceView.value = "missions"; await loadAIMissions(); await loadAIMissionDetail(started.mission.id);
      } catch (error) { aiMissionError.value = error.message || "Copilot 暂时无法创建 Mission。"; }
      finally { entryCopilotLoading.value = false; }
    }

    async function loadEnterpriseFiles() {
      try { enterpriseFiles.value = await readResponse(await fetchWithTimeout(`${API_BASE_URL}/api/files`)); }
      catch (error) { enterpriseFileError.value = error.message || "客户资料暂时无法加载。"; }
    }

    async function loadDocumentAnalytics() {
      try { documentAnalytics.value = await readResponse(await fetchWithTimeout(`${API_BASE_URL}/api/files/analytics`)); }
      catch (_) { documentAnalytics.value = null; }
    }

    async function uploadEnterpriseFile(event) {
      const file = event.target?.files?.[0]; if (!file || enterpriseFileLoading.value) return;
      enterpriseFileLoading.value = true; enterpriseFileError.value = "";
      try {
        const form = new FormData(); form.append("file", file);
        const result = await readResponse(await fetchWithTimeout(`${API_BASE_URL}/api/files/upload`, { method: "POST", body: form }));
        selectedEnterpriseFile.value = result; await Promise.all([loadEnterpriseFiles(), loadDocumentAnalytics()]); activeWorkspaceView.value = "document-intelligence";
      } catch (error) { enterpriseFileError.value = error.message || "文件上传或解析失败。"; }
      finally { enterpriseFileLoading.value = false; event.target.value = ""; }
    }

    async function openEnterpriseFile(fileId) {
      try { selectedEnterpriseFile.value = await readResponse(await fetchWithTimeout(`${API_BASE_URL}/api/files/${fileId}/analysis`)); activeWorkspaceView.value = "document-intelligence"; }
      catch (error) { enterpriseFileError.value = error.message || "资料分析暂时无法加载。"; }
    }

    async function createMissionFromDocument() {
      if (!selectedEnterpriseFile.value || enterpriseFileLoading.value) return;
      enterpriseFileLoading.value = true; enterpriseFileError.value = "";
      try {
        const result = await readResponse(await fetchWithTimeout(`${API_BASE_URL}/api/files/${selectedEnterpriseFile.value.id}/create-mission`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ confirmed: true }) }));
        selectedAIMission.value = result.mission; await loadAIMissions(); await loadAIMissionDetail(result.mission.id); activeWorkspaceView.value = "mission-center";
      } catch (error) { enterpriseFileError.value = error.message || "Mission 创建失败。"; }
      finally { enterpriseFileLoading.value = false; }
    }

    async function runAIMission(missionId) {
      if (!missionId) return;
      aiMissionLoading.value = true; aiMissionError.value = ""; aiMissionDelivery.value = null;
      try {
        const response = await fetchWithTimeout(`${API_BASE_URL}/api/missions/${missionId}/run`, { method: "POST" });
        selectedAIMission.value = await readResponse(response);
        await loadAIMissions();
      } catch (error) { aiMissionError.value = error.message || "Mission 执行失败。"; }
      finally { aiMissionLoading.value = false; }
    }

    async function executeAIWorkerRuntime(missionId) {
      if (!missionId) return;
      aiMissionLoading.value = true; aiMissionError.value = ""; aiMissionDelivery.value = null;
      try {
        await readResponse(await fetchWithTimeout(`${API_BASE_URL}/api/runtime/missions/${missionId}/execute`, { method: "POST" }));
        await loadAIMissionDetail(missionId);
        await loadAIMissions();
      } catch (error) { aiMissionError.value = error.message || "AI Worker 当前无法执行该受控步骤。"; }
      finally { aiMissionLoading.value = false; }
    }

    async function updateMissionControl(action) {
      const missionId = selectedAIMission.value?.id;
      if (!missionId || !['pause', 'resume', 'recover'].includes(action)) return;
      aiMissionLoading.value = true;
      aiMissionError.value = "";
      try {
        await readResponse(await fetchWithTimeout(`${API_BASE_URL}/api/missions/${missionId}/${action}`, { method: "POST" }));
        await loadAIMissionDetail(missionId);
        await loadAIMissions();
      } catch (error) {
        aiMissionError.value = error.message || "This mission control action is not available right now.";
      } finally { aiMissionLoading.value = false; }
    }

    async function reviewAIMission(status) {
      const missionId = selectedAIMission.value?.id;
      if (!missionId) return;
      aiMissionLoading.value = true; aiMissionError.value = "";
      try {
        const response = await fetchWithTimeout(`${API_BASE_URL}/api/missions/${missionId}/review`, {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ status, review_comment: aiMissionReviewComment.value.trim() }),
        });
        const payload = await readResponse(response);
        selectedAIMission.value = payload.mission;
        await loadAIMissions();
      } catch (error) { aiMissionError.value = error.message || "审核状态更新失败。"; }
      finally { aiMissionLoading.value = false; }
    }

    async function reviseAIMission() {
      const missionId = selectedAIMission.value?.id;
      if (!missionId || !aiMissionRevisionSummary.value.trim()) { aiMissionError.value = "请说明需要调整的内容。"; return; }
      aiMissionLoading.value = true; aiMissionError.value = "";
      try {
        const response = await fetchWithTimeout(`${API_BASE_URL}/api/missions/${missionId}/revise`, {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ change_summary: aiMissionRevisionSummary.value.trim() }),
        });
        selectedAIMission.value = await readResponse(response);
        aiMissionRevisionSummary.value = "";
        await loadAIMissions();
      } catch (error) { aiMissionError.value = error.message || "版本修订失败。"; }
      finally { aiMissionLoading.value = false; }
    }

    async function generateAIMissionDelivery() {
      const missionId = selectedAIMission.value?.id;
      if (!missionId) return;
      aiMissionLoading.value = true; aiMissionError.value = "";
      try {
        const response = await fetchWithTimeout(`${API_BASE_URL}/api/missions/${missionId}/delivery`, { method: "POST" });
        const payload = await readResponse(response);
        selectedAIMission.value = payload.mission;
        aiMissionDelivery.value = payload.delivery_package;
        await loadAIMissions();
      } catch (error) { aiMissionError.value = error.message || "Delivery Package 生成失败。"; }
      finally { aiMissionLoading.value = false; }
    }

    async function startFdeMissionDemo() {
      aiMissionForm.value = {
        title: "Demo · 低碳建筑材料企业协作方案",
        mission_type: "SOLUTION",
        goal: "【Demo】企业希望探索低碳建筑材料的性能优化方向，并建立可审阅的科研协作方案。",
      };
      await createAIMission();
      if (selectedAIMission.value?.id) await runAIMission(selectedAIMission.value.id);
    }

    async function createComputerMission() {
      const missionId = selectedAIMission.value?.id;
      if (!missionId || !computerMissionTask.value.trim()) { aiMissionError.value = "请先说明需要 Computer Skill 执行的受控任务。"; return; }
      computerMissionLoading.value = true; aiMissionError.value = "";
      try {
        const response = await fetchWithTimeout(`${API_BASE_URL}/api/computer-missions`, {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ mission_id: missionId, task: computerMissionTask.value.trim(), reason: "Mission Detail 中由用户发起的受控执行请求" }),
        });
        const created = await readResponse(response);
        await readResponse(await fetchWithTimeout(`${API_BASE_URL}/api/computer-missions/${created.id}/analyze`, { method: "POST" }));
        computerMissionTask.value = "";
        await loadAIMissionDetail(missionId);
      } catch (error) { aiMissionError.value = error.message || "Computer Mission 分析失败。"; }
      finally { computerMissionLoading.value = false; }
    }

    async function decideComputerMission(item, decision) {
      computerMissionLoading.value = true; aiMissionError.value = "";
      try {
        const response = await fetchWithTimeout(`${API_BASE_URL}/api/computer-missions/${item.id}/approve`, {
          method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ decision, note: "Mission Center 人工审核" }),
        });
        await readResponse(response);
        await loadAIMissionDetail(selectedAIMission.value?.id);
      } catch (error) { aiMissionError.value = error.message || "Computer Mission 审核或执行失败。"; }
      finally { computerMissionLoading.value = false; }
    }

    async function executeComputerMission(item) {
      computerMissionLoading.value = true; aiMissionError.value = "";
      try {
        await readResponse(await fetchWithTimeout(`${API_BASE_URL}/api/computer-missions/${item.id}/execute`, { method: "POST" }));
        await loadAIMissionDetail(selectedAIMission.value?.id);
      } catch (error) { aiMissionError.value = error.message || "Computer Mission 执行失败。"; }
      finally { computerMissionLoading.value = false; }
    }

    async function markAINotificationRead(notificationId) {
      try {
        await readResponse(await fetchWithTimeout(`${API_BASE_URL}/api/notifications/${notificationId}/read`, { method: "POST" }));
        aiNotifications.value = aiNotifications.value.map((item) => item.id === notificationId ? { ...item, read: true } : item);
      } catch (error) { aiMissionError.value = error.message || "通知状态更新失败。"; }
    }

    async function loadFdeSolutionDetail(solutionId) {
      if (!solutionId) return;
      const response = await fetchWithTimeout(`${API_BASE_URL}/researchos/solutions/${solutionId}`, { method: "GET" });
      selectedFdeSolution.value = await readResponse(response);
      fdeComputerMissions.value = selectedFdeSolution.value.computer_missions || [];
      fdeSolutionVersions.value = selectedFdeSolution.value.versions || [];
    }

    function fdeEvidenceRefs() {
      const generated = fdeSolutionBlueprint.value?.blueprint?.evidence_refs;
      const savedBlueprint = selectedFdeSolution.value?.deliverables?.find((item) => item.deliverable_type === "SOLUTION_BLUEPRINT")?.content?.evidence_refs;
      return Array.isArray(generated) ? generated : (Array.isArray(savedBlueprint) ? savedBlueprint : []);
    }

    function applyFdeSolutionDemo() {
      fdeSolutionForm.value = {
        title: "DEMO · 高校科研知识智能平台建设方案",
        customer_need: "某高校科研团队希望建设科研知识管理与研究决策平台，希望解决论文资料分散、研究方向难分析、科研成果难沉淀的问题。",
        industry: "Higher Education",
        objective: "建立可追溯、Evidence-driven 的研究协作与交付流程。",
      };
      fdeSolutionError.value = "";
    }

    async function createFdeSolution() {
      const payload = fdeSolutionForm.value;
      if (!payload.title.trim() || !payload.customer_need.trim()) {
        fdeSolutionError.value = "请至少填写方案标题和客户需求。";
        return;
      }
      fdeSolutionLoading.value = true; fdeSolutionError.value = "";
      try {
        const response = await fetchWithTimeout(`${API_BASE_URL}/researchos/solutions`, {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ ...payload, title: payload.title.trim(), customer_need: payload.customer_need.trim(), objective: payload.objective.trim() }),
        });
        selectedFdeSolution.value = await readResponse(response);
        fdeSolutionAnalysis.value = null; fdeSolutionBlueprint.value = null; fdeSolutionPackage.value = null; fdeComputerMissions.value = []; fdeSolutionVersions.value = [];
        await loadFdeSolutions();
      } catch (error) { fdeSolutionError.value = error.message || "方案项目创建失败。"; }
      finally { fdeSolutionLoading.value = false; }
    }

    async function analyzeFdeSolution() {
      if (!selectedFdeSolution.value?.id) return;
      fdeSolutionLoading.value = true; fdeSolutionError.value = "";
      try {
        const response = await fetchWithTimeout(`${API_BASE_URL}/researchos/solutions/${selectedFdeSolution.value.id}/analyze`, { method: "POST" });
        fdeSolutionAnalysis.value = await readResponse(response);
        await loadFdeSolutionDetail(selectedFdeSolution.value.id);
      } catch (error) { fdeSolutionError.value = error.message || "需求理解生成失败。"; }
      finally { fdeSolutionLoading.value = false; }
    }

    async function generateFdeSolutionBlueprint() {
      if (!selectedFdeSolution.value?.id) return;
      fdeSolutionLoading.value = true; fdeSolutionError.value = "";
      try {
        const response = await fetchWithTimeout(`${API_BASE_URL}/researchos/solutions/${selectedFdeSolution.value.id}/blueprint`, { method: "POST" });
        fdeSolutionBlueprint.value = await readResponse(response);
        await loadFdeSolutionDetail(selectedFdeSolution.value.id);
      } catch (error) { fdeSolutionError.value = error.message || "Solution Blueprint 生成失败。"; }
      finally { fdeSolutionLoading.value = false; }
    }

    async function reviewFdeSolution(status) {
      if (!selectedFdeSolution.value?.id) return;
      fdeSolutionLoading.value = true; fdeSolutionError.value = "";
      try {
        const response = await fetchWithTimeout(`${API_BASE_URL}/researchos/solutions/${selectedFdeSolution.value.id}/review`, {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ status, reviewer_note: fdeSolutionReviewNote.value.trim() }),
        });
        selectedFdeSolution.value = await readResponse(response);
      } catch (error) { fdeSolutionError.value = error.message || "人工审核状态更新失败。"; }
      finally { fdeSolutionLoading.value = false; }
    }

    async function loadFdeSolutionPackage() {
      if (!selectedFdeSolution.value?.id) return;
      fdeSolutionLoading.value = true; fdeSolutionError.value = "";
      try {
        const response = await fetchWithTimeout(`${API_BASE_URL}/researchos/solutions/${selectedFdeSolution.value.id}/delivery-package`, { method: "GET" });
        fdeSolutionPackage.value = await readResponse(response);
      } catch (error) { fdeSolutionError.value = error.message || "交付包暂时无法读取。"; }
      finally { fdeSolutionLoading.value = false; }
    }

    function beginResearchFromHome(template = "") {
      const goal = (template || researchOsGoal.value || "").trim();
      if (goal) researchOsGoal.value = goal;
      assistantPanelOpen.value = false;
      activeWorkspaceView.value = "insights";
      void loadResearchOsData();
    }

    function sendAssistantToResearch() {
      beginResearchFromHome(assistantDraft.value);
      assistantDraft.value = "";
    }

    async function resumeResearchWorkspace(workspace) {
      if (!workspace?.workspace_id) return;
      activeWorkspaceView.value = "research-workspace";
      await loadResearchWorkspaceDetails(workspace.workspace_id);
    }

    async function loadResearchOsData() {
      if (!identityProfile.value?.workspace?.id) return;
      try {
        const [overviewResponse, agentsResponse] = await Promise.all([
          fetchWithTimeout(`${API_BASE_URL}/researchos/overview`, { method: "GET" }),
          fetchWithTimeout(`${API_BASE_URL}/researchos/agents`, { method: "GET" }),
        ]);
        researchOsOverview.value = await readResponse(overviewResponse);
        const agentData = await readResponse(agentsResponse);
        researchOsAgents.value = Array.isArray(agentData.agents) ? agentData.agents : [];
        try {
          aiWorkerCapabilities.value = await readResponse(
            await fetchWithTimeout(`${API_BASE_URL}/researchos/ai-worker/capabilities`, { method: "GET" }),
          );
        } catch (_) { aiWorkerCapabilities.value = null; }
        // Keep Home's recent-workspace area data-backed from the same live session.
        void loadResearchWorkspaces();
      } catch (error) {
        researchOsError.value = error.message || "ResearchOS 工作空间暂时无法加载。";
      }
    }

    function recordActivity(action, detail) {
      const record = { action, detail, created_at: new Date().toISOString() };
      saveActivityLog(record);
      activityLogs.value = loadActivityLog();
    }

    async function loadSystemStatus() {
      if (systemStatusLoading.value) return;
      systemStatusLoading.value = true;
      systemStatusError.value = "";
      try {
        const response = await fetchWithTimeout(`${API_BASE_URL}/researchos/system-status`, { method: "GET" });
        systemStatus.value = await readResponse(response);
      } catch (error) {
        systemStatusError.value = error.message || "系统状态暂时无法加载。";
      } finally {
        systemStatusLoading.value = false;
      }
    }

    async function loadAgentAnalytics() {
      try { const [metrics, adaptive] = await Promise.all([readResponse(await fetchWithTimeout(`${API_BASE_URL}/api/agent-metrics`)), readResponse(await fetchWithTimeout(`${API_BASE_URL}/api/adaptive-metrics`))]); agentAnalytics.value = metrics; adaptiveAnalytics.value = adaptive; }
      catch (_) { agentAnalytics.value = []; adaptiveAnalytics.value = null; }
    }

    async function loadCopilotAnalytics() {
      try { copilotAnalytics.value = await readResponse(await fetchWithTimeout(`${API_BASE_URL}/api/copilot/analytics`)); }
      catch (_) { copilotAnalytics.value = null; }
    }

    async function loadAgentMemories() {
      try { agentMemories.value = await readResponse(await fetchWithTimeout(`${API_BASE_URL}/api/agent-memory`)); }
      catch (_) { agentMemories.value = []; }
    }

    async function deleteAgentMemory(memoryId) {
      try { await readResponse(await fetchWithTimeout(`${API_BASE_URL}/api/agent-memory/${memoryId}/delete`, { method: "POST" })); await loadAgentMemories(); }
      catch (error) { systemStatusError.value = error.message || "Memory 暂时无法删除。"; }
    }

    async function loadWorkflowDiagnostics() {
      if (diagnosticsLoading.value) return;
      diagnosticsLoading.value = true;
      diagnosticsError.value = "";
      try {
        const response = await fetchWithTimeout(`${API_BASE_URL}/researchos/diagnostics`, { method: "GET" });
        workflowDiagnostics.value = await readResponse(response);
      } catch (error) {
        diagnosticsError.value = error.message || "真实资料链路状态暂时无法检查。";
      } finally {
        diagnosticsLoading.value = false;
      }
    }

    function initializeDemoKnowledge() {
      if (!demoKnowledgeInitialized.value) {
        window.localStorage.setItem(DEMO_KNOWLEDGE_KEY, "true");
        demoKnowledgeInitialized.value = true;
        recordActivity("Demo 知识库初始化", "已加载低碳建筑材料案例的论文、专利与项目资料展示卡。");
      }
      activeWorkspaceView.value = "system";
    }

    function toggleResearchOsAgent(agentId) {
      const selected = researchOsSelectedAgents.value;
      researchOsSelectedAgents.value = selected.includes(agentId)
        ? selected.filter((item) => item !== agentId)
        : [...selected, agentId];
    }

    function applyResearchOsDemo() {
      researchOsGoal.value = "面向某高校建筑材料实验室，分析低碳建筑材料未来研究方向，识别技术趋势、潜在创新机会，并规划可形成的论文、专利与研究任务。";
      researchOsSelectedAgents.value = ["literature", "knowledge", "trend", "innovation", "project", "report"];
      researchOsTaskResult.value = null;
      researchOsError.value = "已填充预设科研任务。请确保论文库已有相关已索引资料后开始运行。";
      activeWorkspaceView.value = "tasks";
    }

    async function runResearchOsTask() {
      const goal = researchOsGoal.value.trim();
      if (!goal || researchOsTaskLoading.value) return;
      researchOsTaskLoading.value = true;
      researchOsError.value = "";
      researchOsTaskResult.value = null;
      recordActivity("科研任务创建", goal);
      try {
        const response = await fetchWithTimeout(`${API_BASE_URL}/researchos/tasks/run`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            user_goal: goal,
            selected_agents: researchOsSelectedAgents.value,
            paper_ids: [],
            workspace_id: selectedResearchWorkspace.value?.workspace_id || null,
          }),
        });
        researchOsTaskResult.value = await readResponse(response);
        if (researchOsTaskResult.value.research_workspace?.workspace_id) {
          selectedResearchWorkspace.value = researchOsTaskResult.value.research_workspace;
          await loadResearchWorkspaceDetails(selectedResearchWorkspace.value.workspace_id);
        }
        recordActivity("Agent 执行完成", "Research Master 已完成科研任务编排与专项分析输出。");
      } catch (error) {
        researchOsError.value = error.message || "科研任务执行失败，请稍后重试。";
      } finally {
        researchOsTaskLoading.value = false;
      }
    }

    async function loadResearchWorkspaces() {
      workspaceIntelligenceLoading.value = true;
      workspaceIntelligenceError.value = "";
      try {
        const response = await fetchWithTimeout(`${API_BASE_URL}/researchos/research-workspaces`, { method: "GET" });
        researchWorkspaces.value = await readResponse(response);
        if (!selectedResearchWorkspace.value && researchWorkspaces.value.length) {
          await loadResearchWorkspaceDetails(researchWorkspaces.value[0].workspace_id);
        }
      } catch (error) {
        workspaceIntelligenceError.value = error.message || "Research Workspace 暂时无法加载。";
      } finally {
        workspaceIntelligenceLoading.value = false;
      }
    }

    async function loadResearchWorkspaceDetails(workspaceId) {
      if (!workspaceId) return;
      workspaceIntelligenceLoading.value = true;
      workspaceIntelligenceError.value = "";
      try {
        const [workspaceResponse, qualityResponse, decisionResponse, membersResponse, workflowResponse, reviewsResponse, graphResponse] = await Promise.all([
          fetchWithTimeout(`${API_BASE_URL}/researchos/research-workspaces/${workspaceId}`, { method: "GET" }),
          fetchWithTimeout(`${API_BASE_URL}/researchos/research-workspaces/${workspaceId}/quality`, { method: "GET" }),
          fetchWithTimeout(`${API_BASE_URL}/researchos/research-workspaces/${workspaceId}/decision-candidate`, { method: "GET" }),
          fetchWithTimeout(`${API_BASE_URL}/researchos/research-workspaces/${workspaceId}/members`, { method: "GET" }),
          fetchWithTimeout(`${API_BASE_URL}/researchos/research-workspaces/${workspaceId}/workflow`, { method: "GET" }),
          fetchWithTimeout(`${API_BASE_URL}/researchos/research-workspaces/${workspaceId}/reviews`, { method: "GET" }),
          fetchWithTimeout(`${API_BASE_URL}/researchos/research-workspaces/${workspaceId}/evidence-graph`, { method: "GET" }),
        ]);
        selectedResearchWorkspace.value = await readResponse(workspaceResponse);
        workspaceQuality.value = await readResponse(qualityResponse);
        workspaceDecisionCandidate.value = await readResponse(decisionResponse);
        workspaceMembers.value = await readResponse(membersResponse);
        workspaceWorkflow.value = await readResponse(workflowResponse);
        workspaceReviews.value = await readResponse(reviewsResponse);
        workspaceEvidenceGraph.value = await readResponse(graphResponse);
        workspaceDeliverable.value = null;
      } catch (error) {
        workspaceIntelligenceError.value = error.message || "研究工作空间详情暂时无法加载。";
      } finally {
        workspaceIntelligenceLoading.value = false;
      }
    }

    async function generateWorkspaceDeliverable(deliverableType) {
      const workspaceId = selectedResearchWorkspace.value?.workspace_id;
      if (!workspaceId || workspaceDeliverableLoading.value) return;
      workspaceDeliverableLoading.value = true;
      workspaceIntelligenceError.value = "";
      try {
        const response = await fetchWithTimeout(`${API_BASE_URL}/researchos/research-workspaces/${workspaceId}/deliverables/${deliverableType}`, { method: "POST" });
        workspaceDeliverable.value = await readResponse(response);
      } catch (error) {
        workspaceIntelligenceError.value = error.message || "科研交付物草案暂时无法生成。";
      } finally {
        workspaceDeliverableLoading.value = false;
      }
    }

    async function reviewWorkspaceItem(itemId, status) {
      const workspaceId = selectedResearchWorkspace.value?.workspace_id;
      if (!workspaceId || workspaceReviewLoading.value) return;
      workspaceReviewLoading.value = true;
      workspaceIntelligenceError.value = "";
      try {
        const response = await fetchWithTimeout(`${API_BASE_URL}/researchos/research-workspaces/${workspaceId}/reviews/${itemId}`, {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ reviewer_role: "reviewer", status, reviewer_note: "由 Workspace 审核中心确认。" }),
        });
        await readResponse(response);
        await loadResearchWorkspaceDetails(workspaceId);
      } catch (error) {
        workspaceIntelligenceError.value = error.message || "审核状态暂时无法更新。";
      } finally {
        workspaceReviewLoading.value = false;
      }
    }

    async function generateResearchBrief() {
      const workspaceId = selectedResearchWorkspace.value?.workspace_id;
      if (!workspaceId || workspaceDeliverableLoading.value) return;
      workspaceDeliverableLoading.value = true;
      workspaceIntelligenceError.value = "";
      try {
        const response = await fetchWithTimeout(`${API_BASE_URL}/researchos/research-workspaces/${workspaceId}/research-brief`, { method: "POST" });
        workspaceDeliverable.value = await readResponse(response);
        await loadResearchWorkspaceDetails(workspaceId);
      } catch (error) {
        workspaceIntelligenceError.value = error.message || "Research Brief 需要完成 Evidence Review 后才能生成。";
      } finally {
        workspaceDeliverableLoading.value = false;
      }
    }

    function applyResearchWorkspaceDemo() {
      researchOsGoal.value = "【Demo案例】实验室准备研究 RAG 优化方向：比较现有资料中的方法效果差异，并形成需要人工审核的研究简报。";
      researchOsSelectedAgents.value = ["literature", "knowledge", "trend", "innovation", "report"];
      researchOsError.value = "Demo案例仅预填研究目标；系统仍只会使用已上传并索引的真实资料。";
      activeWorkspaceView.value = "tasks";
    }

    function researchTimelineLabel(phase) {
      const labels = {
        task_understanding: "Understanding Goal", strategy_planning: "Building Strategy",
        query_rewrite: "Searching Evidence", retrieval: "Searching Evidence",
        rerank: "Comparing Research", evidence_validation: "Comparing Research",
        conflict_check: "Detecting Conflict", intermediate_decision: "Human Review",
        final_synthesis: "Deliverable", loop_completion: "Deliverable",
      };
      return labels[phase] || "Research Step";
    }

    async function loadAutonomousWorkspace() {
      autonomousError.value = "";
      try {
        const [runsResponse, toolsResponse, memoryResponse] = await Promise.all([
          fetchWithTimeout(`${API_BASE_URL}/researchos/autonomous-runs`, { method: "GET" }),
          fetchWithTimeout(`${API_BASE_URL}/researchos/autonomous-runs/tools`, { method: "GET" }),
          fetchWithTimeout(`${API_BASE_URL}/researchos/research-memory`, { method: "GET" }),
        ]);
        autonomousRuns.value = await readResponse(runsResponse);
        const toolData = await readResponse(toolsResponse);
        autonomousTools.value = Array.isArray(toolData.tools) ? toolData.tools : [];
        autonomousMemory.value = await readResponse(memoryResponse);
      } catch (error) {
        autonomousError.value = error.message || "自主科研工作空间暂时无法加载。";
      }
    }

    async function runAutonomousResearch() {
      const goal = autonomousGoal.value.trim();
      if (!goal || autonomousLoading.value) return;
      autonomousLoading.value = true;
      autonomousError.value = "";
      autonomousRun.value = null;
      recordActivity("自主科研任务创建", goal);
      try {
        const response = await fetchWithTimeout(`${API_BASE_URL}/researchos/autonomous-runs`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ goal, paper_ids: [], generate_docx: false }),
        });
        autonomousRun.value = await readResponse(response);
        autonomousRuns.value = [autonomousRun.value, ...autonomousRuns.value.filter((item) => item.id !== autonomousRun.value.id)];
        recordActivity("自主科研任务完成", autonomousRun.value.status === "completed" ? "Research Brain 已完成受控工具调用与研究交付。" : "Research Brain 已完成资料覆盖检查，等待补充可验证依据。");
      } catch (error) {
        autonomousError.value = error.message || "自主科研任务执行失败，请稍后重试。";
      } finally {
        autonomousLoading.value = false;
      }
    }

    async function loadResearchWorkerWorkspace() {
      workerError.value = "";
      try {
        const response = await fetchWithTimeout(`${API_BASE_URL}/researchos/research-worker/tools`, { method: "GET" });
        const data = await readResponse(response);
        workerTools.value = Array.isArray(data.tools) ? data.tools : [];
      } catch (error) {
        workerError.value = error.message || "Research Worker 工具状态暂时无法加载。";
      }
    }

    async function loadOperatorStudio() {
      operatorError.value = "";
      try {
        const [toolsResponse, tasksResponse] = await Promise.all([
          fetchWithTimeout(`${API_BASE_URL}/researchos/operator/tools`, { method: "GET" }),
          fetchWithTimeout(`${API_BASE_URL}/researchos/operator/tasks`, { method: "GET" }),
        ]);
        const toolData = await readResponse(toolsResponse);
        operatorTools.value = Array.isArray(toolData.tools) ? toolData.tools : [];
        operatorTasks.value = await readResponse(tasksResponse);
        operatorTask.value = operatorTask.value || operatorTasks.value[0] || null;
      } catch (error) {
        operatorError.value = error.message || "Operator Studio 暂时无法加载。";
      }
    }

    async function runOperatorTask() {
      const goal = operatorGoal.value.trim();
      if (!goal || operatorLoading.value) return;
      operatorLoading.value = true;
      operatorError.value = "";
      try {
        const response = await fetchWithTimeout(`${API_BASE_URL}/researchos/operator/tasks`, {
          method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ user_goal: goal }),
        });
        operatorTask.value = await readResponse(response);
        operatorTasks.value = [operatorTask.value, ...operatorTasks.value.filter((item) => item.id !== operatorTask.value.id)];
        recordActivity("Research Operator 任务创建", goal);
      } catch (error) {
        operatorError.value = error.message || "Research Operator 任务执行失败。";
      } finally { operatorLoading.value = false; }
    }

    async function loadComputerStudio() {
      computerError.value = "";
      try {
        const [toolsResponse, tasksResponse, memoryResponse, environmentResponse, catalogResponse] = await Promise.all([
          fetchWithTimeout(`${API_BASE_URL}/researchos/computer/tools`, { method: "GET" }),
          fetchWithTimeout(`${API_BASE_URL}/researchos/computer/tasks`, { method: "GET" }),
          fetchWithTimeout(`${API_BASE_URL}/researchos/computer/memory`, { method: "GET" }),
          fetchWithTimeout(`${API_BASE_URL}/researchos/computer/environment`, { method: "GET" }),
          fetchWithTimeout(`${API_BASE_URL}/researchos/computer/pro/catalog`, { method: "GET" }),
        ]);
        const toolData = await readResponse(toolsResponse);
        computerTools.value = Array.isArray(toolData.tools) ? toolData.tools : [];
        computerTasks.value = await readResponse(tasksResponse);
        computerMemory.value = await readResponse(memoryResponse);
        computerEnvironment.value = await readResponse(environmentResponse);
        computerProCatalog.value = await readResponse(catalogResponse);
        // Do not let a late history request overwrite a newly generated
        // plan-only preview with the previous execution run.
        if (!computerPlanPreview.value) {
          computerTask.value = computerTask.value || computerTasks.value[0] || null;
          if (computerTask.value?.id) {
            try {
              const detailResponse = await fetchWithTimeout(`${API_BASE_URL}/researchos/computer/tasks/${computerTask.value.id}`, { method: "GET" });
              computerTask.value = await readResponse(detailResponse);
            } catch (_error) {
              // Older P8 sessions have no Pro events. Their existing actions
              // remain the compatible fallback shown by the timeline.
            }
          }
        }
      } catch (error) { computerError.value = error.message || "Computer Studio 暂时无法加载。"; }
    }

    async function previewComputerPlan() {
      const goal = computerGoal.value.trim();
      if (!goal || computerPlanLoading.value) return;
      computerPlanLoading.value = true; computerError.value = "";
      try {
        const response = await fetchWithTimeout(`${API_BASE_URL}/researchos/computer/plan`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ user_goal: goal }) });
        computerPlanPreview.value = await readResponse(response);
        // A fresh plan must be visually distinct from a previously persisted
        // execution run. The historical task remains available in the API list.
        computerTask.value = null;
      } catch (error) { computerError.value = error.message || "任务计划暂时无法生成。"; }
      finally { computerPlanLoading.value = false; }
    }

    async function runComputerTask() {
      const goal = computerGoal.value.trim();
      if (!goal || computerLoading.value || !computerPlanPreview.value) return;
      computerLoading.value = true; computerError.value = "";
      try {
        const createResponse = await fetchWithTimeout(`${API_BASE_URL}/researchos/computer/use/tasks`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ goal, execution_mode: computerMode.value }) });
        const created = await readResponse(createResponse);
        computerAutonomousId.value = created.id;
        const response = await fetchWithTimeout(`${API_BASE_URL}/researchos/computer/use/${created.id}/start`, { method: "POST" });
        const autonomous = await readResponse(response);
        computerTask.value = { ...(autonomous.computer_task || {}), events: autonomous.timeline || autonomous.computer_task?.events || [], activity: autonomous.activity || [], mission: autonomous.mission || null, codeReview: autonomous.code_review || [], verificationPlan: autonomous.verification_plan || [], diffSummary: autonomous.diff_summary || {}, autonomousStatus: autonomous.status, autonomousArtifacts: autonomous.artifacts || [] };
        // The plan preview is ephemeral. Once the backend has actually run a
        // controlled task, show the persisted execution event stream instead.
        computerPlanPreview.value = null;
        computerTasks.value = [computerTask.value, ...computerTasks.value.filter((item) => item.id !== computerTask.value.id)];
        recordActivity("Computer Skill 任务创建", goal);
      } catch (error) { computerError.value = error.message || "Computer Skill 任务创建失败。"; }
      finally { computerLoading.value = false; }
    }

    function applyComputerTemplate(template) { computerGoal.value = template; computerPlanPreview.value = null; computerError.value = ""; }

    async function loadCopilotCenter() {
      copilotLoading.value = true; copilotError.value = "";
      try {
        if (!researchWorkspaces.value.length) await loadResearchWorkspaces();
        const workspace = selectedResearchWorkspace.value || researchWorkspaces.value[0];
        const memoryResponse = await fetchWithTimeout(API_BASE_URL + "/researchos/copilot/memory");
        const actionsResponse = await fetchWithTimeout(API_BASE_URL + "/researchos/copilot/actions");
        copilotMemory.value = await readResponse(memoryResponse); copilotActions.value = await readResponse(actionsResponse);
        copilotInsight.value = workspace ? await readResponse(await fetchWithTimeout(API_BASE_URL + "/researchos/research-workspaces/" + workspace.workspace_id + "/copilot")) : null;
      } catch (error) { copilotError.value = error.message || "Research Copilot 暂时无法加载。"; }
      finally { copilotLoading.value = false; }
    }
    async function createCopilotSuggestion(item) {
      if (!copilotInsight.value || copilotLoading.value) return; copilotLoading.value = true;
      try {
        const response = await fetchWithTimeout(API_BASE_URL + "/researchos/copilot/actions", {method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({workspace_id:copilotInsight.value.workspace_id,title:item.title,rationale:item.rationale,evidence_refs:item.evidence_refs||[]})});
        const action=await readResponse(response); copilotActions.value=[action,...copilotActions.value];
      } catch(error) { copilotError.value=error.message||"建议无法加入人工确认队列。"; } finally { copilotLoading.value=false; }
    }
    async function reviewCopilotAction(action, status) {
      if(copilotLoading.value)return; copilotLoading.value=true;
      try { const response=await fetchWithTimeout(API_BASE_URL+"/researchos/copilot/actions/"+action.id+"/review",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({status})}); const updated=await readResponse(response); copilotActions.value=copilotActions.value.map(item=>item.id===updated.id?updated:item); }
      catch(error){copilotError.value=error.message||"人工确认状态更新失败。";} finally{copilotLoading.value=false;}
    }

    async function reviewComputerAction(action, decision) {
      if (!action?.id || computerLoading.value) return;
      computerLoading.value = true; computerError.value = "";
      try {
        const suffix = decision === "approve" ? "approve" : "reject";
        if (computerAutonomousId.value && decision === "approve") {
          const response = await fetchWithTimeout(`${API_BASE_URL}/researchos/computer/use/${computerAutonomousId.value}/approve`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ reviewer_note: "通过 Computer Studio 提交的人工审核" }) });
          const autonomous = await readResponse(response);
          computerTask.value = { ...(autonomous.computer_task || {}), events: autonomous.timeline || autonomous.computer_task?.events || [], activity: autonomous.activity || [], mission: autonomous.mission || null, codeReview: autonomous.code_review || [], verificationPlan: autonomous.verification_plan || [], diffSummary: autonomous.diff_summary || {}, autonomousStatus: autonomous.status, autonomousArtifacts: autonomous.artifacts || [] };
        } else {
          const response = await fetchWithTimeout(`${API_BASE_URL}/researchos/computer/actions/${action.id}/${suffix}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ reviewer_note: "通过 Computer Studio 提交的人工审核" }) });
          computerTask.value = await readResponse(response);
        }
        computerTasks.value = [computerTask.value, ...computerTasks.value.filter((item) => item.id !== computerTask.value.id)];
        recordActivity("Computer Skill 人工审核", decision === "approve" ? "已批准受控操作。" : "已拒绝受控操作。");
      } catch (error) { computerError.value = error.message || "Computer Action 审核失败。"; }
      finally { computerLoading.value = false; }
    }

    function applyOperatorTemplate(template) {
      operatorGoal.value = template;
      operatorError.value = "";
    }

    async function reviewOperatorTask(decision) {
      if (!operatorTask.value || operatorLoading.value) return;
      operatorLoading.value = true;
      operatorError.value = "";
      try {
        const action = decision === "approve" ? "approve" : "reject";
        const response = await fetchWithTimeout(`${API_BASE_URL}/researchos/operator/tasks/${operatorTask.value.id}/${action}`, {
          method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ reviewer_note: "通过 Operator Studio 提交的人工审核" }),
        });
        operatorTask.value = await readResponse(response);
        operatorTasks.value = [operatorTask.value, ...operatorTasks.value.filter((item) => item.id !== operatorTask.value.id)];
        recordActivity("Research Operator 人工审核", decision === "approve" ? "已批准待审核草稿。" : "已拒绝待审核草稿。");
      } catch (error) {
        operatorError.value = error.message || "人工审核状态更新失败。";
      } finally { operatorLoading.value = false; }
    }

    async function loadEnterpriseWorkspace() {
      workspaceLoading.value = true; workspaceError.value = "";
      try {
        const response = await fetchWithTimeout(`${API_BASE_URL}/researchos/workspaces`, { method: "GET" });
        workspaces.value = await readResponse(response);
        activeResearchWorkspace.value = activeResearchWorkspace.value || workspaces.value[0] || null;
        if (activeResearchWorkspace.value) await loadResearchTasks();
      } catch (error) { workspaceError.value = error.message || "工作空间暂时无法加载。"; }
      finally { workspaceLoading.value = false; }
    }

    async function createResearchWorkspace() {
      const name = workspaceName.value.trim(); if (!name || workspaceLoading.value) return;
      workspaceLoading.value = true; workspaceError.value = "";
      try {
        const response = await fetchWithTimeout(`${API_BASE_URL}/researchos/workspaces`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name }) });
        activeResearchWorkspace.value = await readResponse(response); workspaces.value = [activeResearchWorkspace.value, ...workspaces.value];
        recordActivity("Research Workspace 已创建", name); await loadResearchTasks();
      } catch (error) { workspaceError.value = error.message || "创建工作空间失败。"; }
      finally { workspaceLoading.value = false; }
    }

    async function loadResearchTasks() {
      if (!activeResearchWorkspace.value) return;
      taskCenterLoading.value = true;
      try { const response = await fetchWithTimeout(`${API_BASE_URL}/researchos/tasks?workspace_id=${encodeURIComponent(activeResearchWorkspace.value.id)}`, { method: "GET" }); researchTasks.value = await readResponse(response); }
      catch (error) { workspaceError.value = error.message || "任务中心暂时无法加载。"; }
      finally { taskCenterLoading.value = false; }
    }

    async function createResearchTask() {
      if (!activeResearchWorkspace.value || !taskName.value.trim()) return;
      taskCenterLoading.value = true;
      try {
        const response = await fetchWithTimeout(`${API_BASE_URL}/researchos/workspaces/${activeResearchWorkspace.value.id}/tasks`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name: taskName.value.trim(), task_type: taskType.value, worker_run_id: workerRun.value?.run_id || "", project_id: pendingTaskProject.value?.id || null, decision_id: pendingTaskProject.value?.decision_id || null, evidence_refs: pendingTaskProject.value?.evidence_refs || [] }) });
        researchTasks.value = [await readResponse(response), ...researchTasks.value]; taskName.value = ""; pendingTaskProject.value = null;
      } catch (error) { workspaceError.value = error.message || "创建科研任务失败。"; }
      finally { taskCenterLoading.value = false; }
    }

    async function loadAgentMonitor() {
      try { const response = await fetchWithTimeout(`${API_BASE_URL}/researchos/agent-monitor`, { method: "GET" }); agentMonitor.value = await readResponse(response); }
      catch (error) { workspaceError.value = error.message || "Agent监控面板暂时无法加载。"; }
    }

    async function loadClientDelivery() {
      if (!workerRun.value?.run_id) return;
      deliveryLoading.value = true;
      try { const response = await fetchWithTimeout(`${API_BASE_URL}/researchos/client-delivery/${workerRun.value.run_id}`, { method: "GET" }); deliveryPreview.value = await readResponse(response); }
      catch (error) { workspaceError.value = error.message || "交付报告暂时无法生成。"; }
      finally { deliveryLoading.value = false; }
    }

    async function exportClientDelivery() {
      if (!workerRun.value?.run_id || deliveryLoading.value) return;
      deliveryLoading.value = true;
      try { const response = await fetchWithTimeout(`${API_BASE_URL}/researchos/client-delivery/export`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ worker_run_id: workerRun.value.run_id }) }); const data = await readResponse(response); recordActivity("客户交付报告已导出", `${data.path} · ${data.notice}`); window.alert(`PDF 已生成：${data.path}\n${data.notice}`); }
      catch (error) { workspaceError.value = error.message || "导出报告失败。"; }
      finally { deliveryLoading.value = false; }
    }

    async function refreshResearchWorkerRun(runId) {
      const response = await fetchWithTimeout(`${API_BASE_URL}/researchos/research-worker/${runId}`, { method: "GET" });
      workerRun.value = await readResponse(response);
      const timelineResponse = await fetchWithTimeout(`${API_BASE_URL}/researchos/research-worker/${runId}/timeline`, { method: "GET" });
      workerTimeline.value = await readResponse(timelineResponse);
      return workerRun.value;
    }

    async function runResearchWorker() {
      const goal = workerGoal.value.trim();
      if (!goal || workerLoading.value) return;
      workerLoading.value = true;
      workerError.value = "";
      workerRun.value = null;
      workerTimeline.value = [];
      workerReviewDecision.value = "";
      workerReviewNote.value = "";
      recordActivity("科研执行任务创建", goal);
      try {
        const response = await fetchWithTimeout(`${API_BASE_URL}/researchos/research-worker/run`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ goal }),
        });
        const created = await readResponse(response);
        await refreshResearchWorkerRun(created.run_id);
        recordActivity("科研执行任务完成", workerRun.value.status === "completed" ? "Research Worker 已生成待复核交付物。" : "Research Worker 等待补充可验证资料或人工确认。");
      } catch (error) {
        workerError.value = error.message || "Research Worker 执行失败，请稍后重试。";
      } finally {
        workerLoading.value = false;
      }
    }

    function applyWorkerTemplate(template) {
      workerGoal.value = template;
      workerRun.value = null;
      workerTimeline.value = [];
      workerError.value = "";
      workerReviewDecision.value = "";
      workerReviewNote.value = "";
    }

    function applyWorkerDemo() {
      applyWorkerTemplate("【Demo案例】寻找低碳建筑材料性能优化方案：扫描资料、分析已有实验数据、检索知识库，并生成待人工确认的技术路线建议。");
      activeWorkspaceView.value = "worker";
    }

    function reviewResearchWorker(decision) {
      workerReviewDecision.value = decision;
      const labels = { accepted: "接受建议", modified: "修改后接受", rejected: "驳回建议" };
      recordActivity("Research Worker 人工审核", `${labels[decision] || decision}；仅记录审核意图，不会自动创建 Action。`);
    }

    async function assessResearchValue() {
      if (!researchOsGoal.value.trim() || valueAssessmentLoading.value) return;
      valueAssessmentLoading.value = true;
      researchOsError.value = "";
      try {
        const response = await fetchWithTimeout(`${API_BASE_URL}/researchos/value-assessment`, {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ research_goal: researchOsGoal.value.trim(), paper_ids: [] }),
        });
        valueAssessment.value = await readResponse(response);
      } catch (error) {
        researchOsError.value = error.message || "科研价值评估失败。";
      } finally {
        valueAssessmentLoading.value = false;
      }
    }

    async function generateLabProfile() {
      if (labProfileLoading.value) return;
      labProfileLoading.value = true;
      researchOsError.value = "";
      try {
        const response = await fetchWithTimeout(`${API_BASE_URL}/researchos/lab-profile/generate`, { method: "POST" });
        labProfile.value = await readResponse(response);
      } catch (error) {
        researchOsError.value = error.message || "实验室能力画像生成失败。";
      } finally {
        labProfileLoading.value = false;
      }
    }

    async function loadEvidenceCenter() {
      if (evidenceLoading.value) return;
      evidenceLoading.value = true;
      evidenceError.value = "";
      try {
        const response = await fetchWithTimeout(`${API_BASE_URL}/researchos/evidence?limit=24`, { method: "GET" });
        const data = await readResponse(response);
        evidenceItems.value = Array.isArray(data.items) ? data.items : [];
      } catch (error) {
        evidenceError.value = error.message || "证据中心暂时无法加载。";
      } finally {
        evidenceLoading.value = false;
      }
    }

    function documentTypeLabel(documentType) {
      const labels = {
        paper: "论文",
        patent: "专利",
        experiment_report: "实验报告",
        project_material: "项目资料",
      };
      return labels[documentType] || "科研资料";
    }

    function knowledgeAssetSummary(paper) {
      const status = paper?.quality_status || paper?.analysis_status;
      if (["ready", "indexed"].includes(status)) {
        return "资料已完成解析与知识索引，可进入多论文检索、创新机会分析和项目规划。";
      }
      if (status === "parsed") {
        return "资料已完成文本解析，等待建立知识索引后参与团队知识探索。";
      }
      return "资料正在准备中，完成解析后可进入 AI 科研工作流。";
    }

    function knowledgeAssetAgents(paper) {
      const status = paper?.quality_status || paper?.analysis_status;
      return ["Knowledge Agent", ...( ["ready", "indexed"].includes(status) ? ["Research Master"] : ["等待索引"] )];
    }

    function applyFdeDeliveryDemo() {
      projectForm.value = {
        name: "低碳建筑材料企业横向项目",
        enterprise_requirement: "企业希望开发低碳建筑材料，兼顾材料性能、工程适用性与可形成的科研成果。",
        research_goal: "识别实验室技术匹配方向、潜在创新机会和可验证的研究任务。",
        technology_route: "以团队知识库证据为基础，形成材料路线与验证建议。",
        paper_plan: "围绕材料机理、性能验证与工程适用性规划论文方向。",
        patent_plan: "围绕配方、制备工艺或应用方法评估可申请的专利方向。",
        outcome_management: "形成阶段技术交流材料、研究任务清单与成果规划。",
        status: "需求分析",
      };
      projectMatchResult.value = null;
      projectError.value = "已填充 FDE 演示案例。创建项目后可运行 Project Agent 需求匹配。";
      activeWorkspaceView.value = "projects";
    }

    function startDemoMode() {
      projectForm.value = {
        name: "低碳建筑材料企业横向项目",
        enterprise_requirement: "企业希望开发低碳建筑材料，兼顾材料性能、工程适用性与可形成的科研成果。",
        research_goal: "识别实验室技术匹配方向、潜在创新机会和可验证的研究任务。",
        technology_route: "以团队知识库证据为基础，形成材料路线与验证建议。",
        paper_plan: "围绕材料机理、性能验证与工程适用性规划论文方向。",
        patent_plan: "围绕配方、制备工艺或应用方法评估可申请的专利方向。",
        outcome_management: "形成阶段技术交流材料、研究任务清单与成果规划。",
        status: "需求分析",
      };
      researchOsGoal.value = researchOsGoal.value.trim() || "面向低碳建筑材料企业需求，分析实验室技术匹配、技术路线、创新机会和成果规划。";
      researchOsSelectedAgents.value = ["literature", "knowledge", "trend", "innovation", "project", "report"];
      workerGoal.value = "【Demo案例】企业希望提升低碳建筑材料性能：扫描已有资料、检索知识库、引用 Evidence，并生成待人工审核的交付报告。";
      workerRun.value = null;
      deliveryPreview.value = null;
      recordActivity("企业客户演示模式", "已加载低碳建筑材料 Demo 流程；展示内容不代表真实科研成果。");
      demoStarted.value = true;
      activeWorkspaceView.value = "demo";
    }

    function openFdeDeliveryRehearsal() {
      fdeStageIndex.value = 0;
      fdeTaskStatuses.value = ["待开始", "待开始", "待开始", "待开始", "待开始"];
      fdeAcceptanceReady.value = false;
      recordActivity("FDE交付演练已启动", "低碳建筑材料 Demo 场景；不写入客户数据或生成真实科研结论。");
      activeWorkspaceView.value = "fde-delivery";
    }

    function startFdeSolutionDemo() {
      fdeDemoStep.value = 0;
      fdeArchitectureSelection.value = "Research Master";
      recordActivity("FDE解决方案演示已启动", "五分钟演示为产品说明流程，不调用模型、不生成真实科研结论。")
      activeWorkspaceView.value = "fde-demo";
    }

    function nextFdeDemoStep() {
      fdeDemoStep.value = Math.min(fdeDemoStep.value + 1, 4);
    }

    function previousFdeDemoStep() {
      fdeDemoStep.value = Math.max(fdeDemoStep.value - 1, 0);
    }

    function toggleFdeNeed(need) {
      fdeSelectedNeeds.value = fdeSelectedNeeds.value.includes(need)
        ? fdeSelectedNeeds.value.filter((item) => item !== need)
        : [...fdeSelectedNeeds.value, need];
    }

    function generateFdeConfiguration() {
      const needs = fdeSelectedNeeds.value;
      const mappings = {
        "知识库建设": "Knowledge Space + RAG + FAISS（仅索引授权上传资料）",
        "文献管理": "论文库 + 解析状态 + 研究报告历史",
        "数据分析": "Research Worker 的受控 File/Data Tool",
        "技术路线规划": "Research Master + Evidence + Human Review",
        "成果管理": "Action / Decision / Project / Outcome 闭环",
      };
      fdeConfigurationResult.value = {
        client_analysis: `${fdeClientType.value}需要将选定资料能力组织为可验证的协作流程。`,
        module_mapping: needs.map((item) => `${item}：${mappings[item]}`),
        implementation_steps: ["确认客户授权资料范围与数据边界", "创建独立 Research Workspace", "按需配置知识空间与受控任务", "以 Evidence 和人工审核完成验收"],
        acceptance_criteria: ["资料状态可见且来源范围明确", "任务输出包含资料依据或明确资料不足", "人工确认后才进入后续项目/成果流程"],
        boundary_note: "Demo方案，仅用于 FDE 解决方案说明；不会自动修改真实系统配置。",
      };
      recordActivity("FDE配置方案已生成", `客户类型：${fdeClientType.value}；所选需求：${needs.join("、") || "未选择"}。`);
    }

    function diagnoseFdeProblem() {
      const problem = fdeProblemInput.value.trim();
      if (!problem) return;
      const text = problem.toLowerCase();
      const hasEvidence = text.includes("证据") || text.includes("引用");
      const hasIndex = text.includes("检索") || text.includes("索引") || text.includes("知识库");
      fdeDiagnosisResult.value = {
        possible_causes: hasEvidence ? ["资料尚未完成索引", "当前任务缺少可引用章节级资料", "需要核验资料授权范围"] : hasIndex ? ["知识库资料数量不足", "文档解析或索引状态未就绪", "问题范围需要更具体"] : ["需要进一步确认客户资料、目标和当前操作步骤"],
        checks: ["检查资料是否已上传、解析并处于可检索状态", "检查 Evidence 是否来自授权资料", "检查任务目标是否明确且处于允许的工具边界内"],
        recommendations: ["先补充或核验资料，再运行受控分析", "用 Evidence 和人工审核确认输出，不将 Demo 内容视为科研结论"],
        customer_confirmation: ["请客户确认资料授权范围", "请客户确认业务目标和验收口径"],
        boundary_note: "这是基于输入关键词的 Demo 诊断清单，不代表真实系统故障定位或科研结论。",
      };
      recordActivity("FDE问题诊断已生成", "已生成需客户确认的检查清单。" );
    }

    function generateFdeDeliveryReport() {
      const profile = fdeScenarioProfile.value;
      const configuredNeeds = fdeConfigurationResult.value?.module_mapping || fdeSelectedNeeds.value.map((item) => `${item}：已纳入 Demo 方案范围`);
      fdeDeliveryReport.value = {
        customer_background: profile.background,
        current_problem: profile.problem,
        requirement_analysis: `围绕 ${fdeDeliveryScenario.value} 的资料协作、可解释分析与人工审核需求，形成受控实施方案。`,
        system_solution: profile.solution,
        module_mapping: configuredNeeds,
        implementation_plan: ["需求调研：确认客户目标、授权资料范围与验收口径", "方案配置：创建演示 Workspace 并选择所需模块", "测试验证：运行受控任务，检查 Evidence 与人工审核流程", "交付确认：输出实施说明，由客户负责人确认"],
        acceptance_criteria: ["客户可查看需求到模块的映射关系", "输出包含 Evidence 或明确提示暂无可验证资料", "所有建议均保留人工确认，不自动创建真实项目或成果"],
        risk_note: "Demo 报告仅用于 FDE 方案沟通。真实实施需以客户授权资料、实际验收和负责人确认作为依据。",
      };
      recordActivity("FDE交付报告已生成", `${fdeDeliveryScenario.value} Demo 场景的客户交付方案已整理。`);
    }

    function selectFdeDeliveryScenario(scenarioName) {
      if (!FDE_SCENARIO_DATA[scenarioName]) return;
      fdeDeliveryScenario.value = scenarioName;
      fdeClientType.value = scenarioName;
      fdeDeliveryReport.value = null;
      recordActivity("FDE场景已切换", `${scenarioName} Demo 场景已选中。`);
    }

    function advanceFdeStage() {
      const next = Math.min(fdeStageIndex.value + 1, 4);
      fdeTaskStatuses.value = fdeTaskStatuses.value.map((status, index) => index < next ? "完成" : index === next ? "执行中" : status);
      fdeStageIndex.value = next;
      if (next === 4) fdeAcceptanceReady.value = true;
    }

    function openDemoStep(step) {
      activeWorkspaceView.value = step.view;
    }

    function projectDeliveryStage(project) {
      if (projectMatchResult.value?.projectName === project.name) return "方案已生成";
      if (project.paper_plan || project.patent_plan) return "成果规划中";
      if (project.technology_route) return "技术路线设计";
      if (project.enterprise_requirement) return "需求分析";
      return "项目创建";
    }

    function selectAdvisorScenario(scenarioId) {
      if (scenarioId === "enterprise") {
        applyFdeDeliveryDemo();
        return;
      }
      if (scenarioId === "explore") {
        researchOsGoal.value = "分析低碳建筑材料未来研究方向，识别技术趋势、创新机会与下一步验证任务。";
        researchOsSelectedAgents.value = ["literature", "knowledge", "trend", "innovation", "report"];
        activeWorkspaceView.value = "tasks";
        return;
      }
      activeWorkspaceView.value = "knowledge";
    }

    async function loadResearchBi() {
      if (researchBiLoading.value) return;
      researchBiLoading.value = true;
      projectError.value = "";
      try {
        const response = await fetchWithTimeout(`${API_BASE_URL}/researchos/bi`, { method: "GET" });
        researchBi.value = await readResponse(response);
      } catch (error) {
        projectError.value = error.message || "科研 BI 数据加载失败。";
      } finally {
        researchBiLoading.value = false;
      }
    }

    async function loadResearchProjects() {
      if (projectLoading.value) return;
      projectLoading.value = true;
      projectError.value = "";
      try {
        const response = await fetchWithTimeout(`${API_BASE_URL}/researchos/projects`, { method: "GET" });
        const data = await readResponse(response);
        researchProjects.value = Array.isArray(data) ? data : [];
        if (!selectedOutcomeProjectId.value && researchProjects.value.length) {
          selectedOutcomeProjectId.value = researchProjects.value[0].id;
          await loadProjectOutcomes();
        }
      } catch (error) {
        projectError.value = error.message || "科研项目加载失败。";
      } finally {
        projectLoading.value = false;
      }
    }

    async function createResearchProject() {
      if (projectLoading.value || !projectForm.value.name.trim()) {
        if (!projectForm.value.name.trim()) projectError.value = "请先填写项目名称。";
        return;
      }
      projectLoading.value = true;
      projectError.value = "";
      try {
        const response = await fetchWithTimeout(`${API_BASE_URL}/researchos/projects`, {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify(projectForm.value),
        });
        const createdProject = await readResponse(response);
        researchProjects.value = [createdProject, ...researchProjects.value];
        if (!selectedOutcomeProjectId.value) selectedOutcomeProjectId.value = researchProjects.value[0].id;
        if (pendingProjectActionId.value) {
          const sourceAction = researchActions.value.find((item) => item.id === pendingProjectActionId.value);
          if (sourceAction) await updateResearchAction(sourceAction, { project_id: createdProject.id });
          pendingProjectActionId.value = "";
        }
        recordActivity("项目更新", `已创建科研项目：${projectForm.value.name}`);
        projectForm.value = { name: "", enterprise_requirement: "", research_goal: "", technology_route: "", paper_plan: "", patent_plan: "", outcome_management: "", status: "planning" };
      } catch (error) {
        projectError.value = error.message || "科研项目创建失败。";
      } finally {
        projectLoading.value = false;
      }
    }

    async function runProjectMatch(project) {
      if (!project?.id || projectMatching.value) return;
      const requirement = project.enterprise_requirement?.trim();
      if (!requirement) {
        projectError.value = "请先在项目中填写企业需求，再运行需求匹配。";
        return;
      }
      projectMatching.value = true;
      projectError.value = "";
      projectMatchResult.value = null;
      try {
        const response = await fetchWithTimeout(`${API_BASE_URL}/researchos/projects/${project.id}/match`, {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ enterprise_requirement: requirement, paper_ids: [] }),
        });
        projectMatchResult.value = {
          ...await readResponse(response),
          projectName: project.name,
          enterprise_requirement: requirement,
        };
        selectedOutcomeProjectId.value = project.id;
        await Promise.all([loadResearchActions(project.id), loadProjectOutcomes()]);
        recordActivity("Agent 执行完成", `Project Agent 已完成「${project.name}」的企业需求匹配。`);
      } catch (error) {
        projectError.value = error.message || "需求匹配执行失败。";
      } finally {
        projectMatching.value = false;
      }
    }

    function actionEvidenceFromSources(sources) {
      return (Array.isArray(sources) ? sources : []).slice(0, 3).map((source) => ({
        evidence_id: [source.paper_id, source.section].filter(Boolean).join(":") || "",
        source: source.filename || source.paper_title || source.source_file || "已上传科研资料",
        chapter: source.section || "正文",
        agent: source.related_agent || "Knowledge Agent",
        score: typeof source.score === "number" ? source.score : null,
        title: source.paper_title || source.source_file || "已上传科研资料",
        detail: [source.section, source.document_type].filter(Boolean).join(" · ") || "章节级资料依据",
      }));
    }

    function actionRationale(sourceAgent, sources) {
      const evidenceCount = actionEvidenceFromSources(sources).length;
      if (evidenceCount) {
        return `${sourceAgent} 基于当前已展示的 Agent 输出及 ${evidenceCount} 条资料依据形成该建议；建议仍需由科研负责人确认，并结合后续验证推进。`;
      }
      return `${sourceAgent} 已形成该建议，但当前没有可验证资料返回；建议先补充资料或人工核验后再推进。`;
    }

    async function loadResearchActions(projectId = "") {
      if (actionLoading.value) return;
      actionLoading.value = true;
      actionError.value = "";
      try {
        const suffix = projectId ? `?project_id=${encodeURIComponent(projectId)}` : "";
        const [actionsResponse, decisionsResponse] = await Promise.all([
          fetchWithTimeout(`${API_BASE_URL}/researchos/actions${suffix}`, { method: "GET" }),
          fetchWithTimeout(`${API_BASE_URL}/researchos/decisions${suffix}`, { method: "GET" }),
        ]);
        researchActions.value = await readResponse(actionsResponse);
        researchDecisions.value = await readResponse(decisionsResponse);
      } catch (error) {
        actionError.value = error.message || "科研行动暂时无法加载。";
      } finally {
        actionLoading.value = false;
      }
    }

    function decisionForAction(actionId) {
      return researchDecisions.value.find((item) => item.action_id === actionId);
    }

    function actionTitle(actionId) {
      return researchActions.value.find((item) => item.id === actionId)?.title || "来源行动已不可用";
    }

    async function createActionFromSuggestion(suggestion, sourceAgent, sourceContext, sources, projectId = "") {
      const title = String(suggestion || "").trim();
      if (!title || !String(sourceContext || "").trim()) {
        actionError.value = "该建议缺少可复核的 Agent 输出上下文，无法创建行动。";
        return;
      }
      actionLoading.value = true;
      actionError.value = "";
      try {
        const response = await fetchWithTimeout(`${API_BASE_URL}/researchos/actions`, {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            project_id: projectId || null,
            title,
            description: "由现有 Agent 分析结果转化为待确认行动；请由科研负责人确认后执行。",
            source_agent: sourceAgent,
            source_context: String(sourceContext).slice(0, 8000),
            evidence_refs: actionEvidenceFromSources(sources),
            rationale: actionRationale(sourceAgent, sources),
          }),
        });
        const created = await readResponse(response);
        researchActions.value = [created, ...researchActions.value];
        recordActivity("行动建议创建", `已从 ${sourceAgent} 输出创建行动：${title}`);
      } catch (error) {
        actionError.value = error.message || "创建科研行动失败。";
      } finally {
        actionLoading.value = false;
      }
    }

    async function updateResearchAction(action, updates) {
      try {
        const response = await fetchWithTimeout(`${API_BASE_URL}/researchos/actions/${action.id}`, {
          method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(updates),
        });
        const updated = await readResponse(response);
        researchActions.value = researchActions.value.map((item) => item.id === updated.id ? updated : item);
      } catch (error) {
        actionError.value = error.message || "更新行动状态失败。";
      }
    }

    async function recordResearchDecision(action, decision) {
      try {
        const response = await fetchWithTimeout(`${API_BASE_URL}/researchos/decisions`, {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ action_id: action.id, decision, decided_by: "科研负责人", note: decisionNotes.value[action.id] || "" }),
        });
        const saved = await readResponse(response);
        researchDecisions.value = [saved, ...researchDecisions.value.filter((item) => item.action_id !== action.id)];
        recordActivity("人工确认", `科研负责人对行动「${action.title}」标记为${decision}。`);
      } catch (error) {
        actionError.value = error.message || "保存确认结果失败。";
      }
    }

    function prepareTaskFromProject(project) {
      const sourceAction = researchActions.value.find((item) => item.project_id === project.id);
      pendingTaskProject.value = { id: project.id, decision_id: decisionForAction(sourceAction?.id)?.id || null, evidence_refs: sourceAction?.evidence_refs || [] };
      taskName.value = `执行项目：${project.name}`;
      taskType.value = "技术路线规划";
      activeWorkspaceView.value = "task-center";
    }

    function prepareProjectFromDecision(action) {
      const savedDecision = decisionForAction(action.id);
      if (!savedDecision || !["已采纳", "已修改"].includes(savedDecision.decision)) {
        actionError.value = "请先采纳或修改后采纳该建议，再创建科研项目。";
        return;
      }
      pendingProjectActionId.value = action.id;
      projectForm.value = {
        name: `研究项目：${action.title}`,
        enterprise_requirement: "",
        research_goal: action.description || action.title,
        technology_route: action.rationale || "请由负责人补充可验证的技术路线。",
        paper_plan: "",
        patent_plan: "",
        outcome_management: `来源行动：${action.title}\nEvidence：${action.evidence_refs?.length || 0} 条（请在创建前人工核验）。`,
        status: "planning",
      };
      activeWorkspaceView.value = "projects";
    }

    async function loadProjectOutcomes() {
      if (!selectedOutcomeProjectId.value || outcomeLoading.value) return;
      outcomeLoading.value = true;
      outcomeError.value = "";
      try {
        const response = await fetchWithTimeout(`${API_BASE_URL}/researchos/projects/${selectedOutcomeProjectId.value}/outcomes`, { method: "GET" });
        projectOutcomes.value = await readResponse(response);
      } catch (error) {
        outcomeError.value = error.message || "项目成果暂时无法加载。";
      } finally {
        outcomeLoading.value = false;
      }
    }

    async function createProjectOutcome() {
      if (!selectedOutcomeProjectId.value || !outcomeForm.value.title.trim() || outcomeLoading.value) {
        outcomeError.value = "请选择项目并填写成果名称。";
        return;
      }
      outcomeLoading.value = true;
      outcomeError.value = "";
      try {
        const response = await fetchWithTimeout(`${API_BASE_URL}/researchos/projects/${selectedOutcomeProjectId.value}/outcomes`, {
          method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(outcomeForm.value),
        });
        projectOutcomes.value = [await readResponse(response), ...projectOutcomes.value];
        recordActivity("成果规划更新", `已新增${outcomeForm.value.outcome_type}成果：${outcomeForm.value.title}`);
        outcomeForm.value = { outcome_type: "论文", title: "", status: "规划中", description: "", source_action_id: "" };
      } catch (error) {
        outcomeError.value = error.message || "创建成果失败。";
      } finally {
        outcomeLoading.value = false;
      }
    }

    async function updateProjectOutcome(outcome, updates) {
      try {
        const response = await fetchWithTimeout(`${API_BASE_URL}/researchos/outcomes/${outcome.id}`, {
          method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(updates),
        });
        const updated = await readResponse(response);
        projectOutcomes.value = projectOutcomes.value.map((item) => item.id === updated.id ? updated : item);
      } catch (error) { outcomeError.value = error.message || "更新成果失败。"; }
    }

    async function updateOutcomeKnowledgeStatus(outcome, knowledgeStatus) {
      try {
        const response = await fetchWithTimeout(`${API_BASE_URL}/researchos/outcomes/${outcome.id}/knowledge-status`, {
          method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ knowledge_status: knowledgeStatus }),
        });
        const updated = await readResponse(response);
        projectOutcomes.value = projectOutcomes.value.map((item) => item.id === updated.id ? updated : item);
      } catch (error) { outcomeError.value = error.message || "更新知识资产状态失败。"; }
    }

    async function deleteProjectOutcome(outcome) {
      if (!window.confirm(`确认删除成果「${outcome.title}」吗？`)) return;
      try {
        const response = await fetchWithTimeout(`${API_BASE_URL}/researchos/outcomes/${outcome.id}`, { method: "DELETE" });
        if (!response.ok) await readResponse(response);
        projectOutcomes.value = projectOutcomes.value.filter((item) => item.id !== outcome.id);
        recordActivity("成果规划更新", `已删除成果：${outcome.title}`);
      } catch (error) { outcomeError.value = error.message || "删除成果失败。"; }
    }

    async function askResearchQuestion() {
      const normalizedQuestion = ragQuestion.value.trim();
      if (ragLoading.value) return;
      if (!normalizedQuestion) {
        ragError.value = "请输入你希望从多篇论文中了解的问题。";
        return;
      }
      if (!libraryPapers.value.length) {
        ragError.value = "论文库暂无可检索资料，请先上传并完成索引。";
        return;
      }
      ragLoading.value = true;
      ragError.value = "";
      ragAnswer.value = "";
      ragSources.value = [];
      ragConfidence.value = "";
      ragAgentPlan.value = null;
      ragAgentTrace.value = null;
      ragRetrievalEvaluation.value = null;
      ragSourceQuality.value = null;
      ragConflictReport.value = null;
      ragSelectedSource.value = null;
      try {
        const response = await fetchWithTimeout(`${API_BASE_URL}/research/questions`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            question: normalizedQuestion,
            paper_ids: ragSelectedPaperIds.value,
          }),
        });
        const data = await readResponse(response);
        ragAnswer.value = typeof data.answer === "string" ? data.answer : "未获得有效回答。";
        ragSources.value = Array.isArray(data.sources) ? data.sources : [];
        ragConfidence.value = typeof data.confidence === "string" ? data.confidence : "low";
        ragAgentPlan.value = data.agent_plan && typeof data.agent_plan === "object" ? data.agent_plan : null;
        ragAgentTrace.value = data.agent_trace && typeof data.agent_trace === "object" ? data.agent_trace : null;
        ragRetrievalEvaluation.value = data.retrieval_evaluation && typeof data.retrieval_evaluation === "object" ? data.retrieval_evaluation : null;
        ragSourceQuality.value = data.source_quality && typeof data.source_quality === "object" ? data.source_quality : null;
        ragConflictReport.value = data.conflict_report && typeof data.conflict_report === "object" ? data.conflict_report : null;
        void loadRagHistory();
      } catch (error) {
        ragError.value = error.message || "知识问答请求失败，请稍后重试。";
      } finally {
        ragLoading.value = false;
      }
    }

    async function loadRagHistory() {
      if (ragHistoryLoading.value) return;
      ragHistoryLoading.value = true;
      try {
        const response = await fetchWithTimeout(`${API_BASE_URL}/research/questions/history`, { method: "GET" });
        const data = await readResponse(response);
        ragHistory.value = Array.isArray(data) ? data : [];
      } catch (error) {
        ragError.value = error.message || "历史知识问答加载失败，请稍后重试。";
      } finally {
        ragHistoryLoading.value = false;
      }
    }

    async function restoreRagHistory(record) {
      if (!record?.id || ragHistoryLoading.value) return;
      ragHistoryLoading.value = true;
      ragError.value = "";
      try {
        const response = await fetchWithTimeout(`${API_BASE_URL}/research/questions/history/${record.id}`, { method: "GET" });
        const data = await readResponse(response);
        ragQuestion.value = data.question || "";
        ragAnswer.value = data.answer || "";
        ragSources.value = Array.isArray(data.sources) ? data.sources : [];
        ragSelectedPaperIds.value = Array.isArray(data.paper_ids) ? data.paper_ids : [];
        ragConfidence.value = "历史记录";
        ragSourceQuality.value = null;
        ragAgentPlan.value = null;
        ragAgentTrace.value = null;
        ragRetrievalEvaluation.value = null;
        ragConflictReport.value = null;
      } catch (error) {
        ragError.value = error.message || "历史知识问答恢复失败，请稍后重试。";
      } finally {
        ragHistoryLoading.value = false;
      }
    }

    async function generateResearchReport() {
      if (ragReportLoading.value || !libraryPapers.value.length) return;
      ragReportLoading.value = true;
      ragReportError.value = "";
      ragReportResult.value = null;
      ragReportSources.value = [];
      ragReportQuality.value = null;
      ragReportTrace.value = null;
      ragReportEvaluation.value = null;
      ragReportConflictReport.value = null;
      try {
        const response = await fetchWithTimeout(`${API_BASE_URL}/research/generate-report`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ report_type: ragReportType.value, paper_ids: ragSelectedPaperIds.value }),
        });
        const data = await readResponse(response);
        ragReportResult.value = data.report && typeof data.report === "object" ? data.report : null;
        ragReportSources.value = Array.isArray(data.sources) ? data.sources : [];
        ragReportQuality.value = data.source_quality && typeof data.source_quality === "object" ? data.source_quality : null;
        ragReportTrace.value = data.agent_trace && typeof data.agent_trace === "object" ? data.agent_trace : null;
        ragReportEvaluation.value = data.retrieval_evaluation && typeof data.retrieval_evaluation === "object" ? data.retrieval_evaluation : null;
        ragReportConflictReport.value = data.conflict_report && typeof data.conflict_report === "object" ? data.conflict_report : null;
        recordActivity("报告生成", `已生成${RESEARCH_REPORT_TASKS.find((item) => item.id === ragReportType.value)?.name || "研究"}报告。`);
      } catch (error) {
        ragReportError.value = error.message || "研究报告生成失败，请稍后重试。";
      } finally {
        ragReportLoading.value = false;
      }
    }

    function showRagSource(source) {
      ragSelectedSource.value = source;
    }

    async function loadResearchOverview() {
      if (overviewLoading.value) return;
      overviewLoading.value = true;
      try {
        const response = await fetchWithTimeout(`${API_BASE_URL}/research/overview`, { method: "GET" });
        researchOverview.value = await readResponse(response);
      } catch {
        // The dashboard remains optional; existing assistant operations should not be blocked.
        researchOverview.value = null;
      } finally {
        overviewLoading.value = false;
      }
    }

    async function loadResearchReports() {
      if (reportsLoading.value) return;
      reportsLoading.value = true;
      reportsError.value = "";
      try {
        const response = await fetchWithTimeout(`${API_BASE_URL}/research/reports`, { method: "GET" });
        const data = await readResponse(response);
        reportRecords.value = Array.isArray(data) ? data : [];
      } catch (error) {
        reportsError.value = error.message || "研究报告加载失败，请稍后重试。";
      } finally {
        reportsLoading.value = false;
      }
    }

    async function viewResearchReport(report) {
      if (!report?.id || reportDetailLoading.value) return;
      reportDetailLoading.value = true;
      reportsError.value = "";
      try {
        const response = await fetchWithTimeout(`${API_BASE_URL}/research/reports/${report.id}`, { method: "GET" });
        const data = await readResponse(response);
        const savedResult = data.analysis_result;
        if (!savedResult || typeof savedResult !== "object" || Array.isArray(savedResult)) {
          throw new Error("保存的分析结果格式异常，无法恢复报告。 ");
        }
        result.value = { ...savedResult, paper_id: savedResult.paper_id || data.paper_id };
        task.value = data.task || task.value;
        scenario.value = data.scenario || scenario.value;
        role.value = data.role || role.value;
        selectedReport.value = data;
        analysisFromLibrary.value = data.source_type === "library";
        selectedLibraryPaper.value = {
          paper_id: data.paper_id,
          title: data.paper_title,
          filename: data.paper_title,
        };
        chatMessages.value = [{ role: "assistant", content: "已恢复历史研究报告。若该论文仍在当前 Agent 会话上下文中，你可以继续追问。" }];
        activeWorkspaceView.value = "assistant";
      } catch (error) {
        reportsError.value = error.message || "历史报告加载失败，请稍后重试。";
      } finally {
        reportDetailLoading.value = false;
      }
    }

    async function loadLibraryPapers() {
      if (!identityProfile.value?.workspace?.id) return;
      if (libraryLoading.value) return;
      libraryLoading.value = true;
      libraryError.value = "";
      try {
        const response = await fetchWithTimeout(`${API_BASE_URL}/research/papers`, { method: "GET" });
        const data = await readResponse(response);
        libraryPapers.value = Array.isArray(data) ? data : [];
      } catch (error) {
        libraryError.value = error.message || "论文库加载失败，请稍后重试。";
      } finally {
        libraryLoading.value = false;
      }
    }

    async function uploadLibraryPaper(event) {
      const file = event.target.files?.[0];
      if (!file || libraryUploading.value) return;
      libraryUploading.value = true;
      libraryError.value = "";
      try {
        const formData = new FormData();
        formData.append("file", file);
        formData.append("document_type", libraryDocumentType.value);
        const response = await fetchWithTimeout(`${API_BASE_URL}/research/papers/upload`, {
          method: "POST",
          body: formData,
        });
        selectedLibraryPaper.value = await readResponse(response);
        libraryPaperDetail.value = null;
        recordActivity("知识库资料上传", `已上传${libraryDocumentType.value}资料：${file.name}`);
        await loadLibraryPapers();
        void loadResearchOverview();
      } catch (error) {
        libraryError.value = error.message || "论文上传失败，请稍后重试。";
      } finally {
        libraryUploading.value = false;
        if (libraryFileInput.value) libraryFileInput.value.value = "";
      }
    }

    async function viewLibraryPaper(paper) {
      if (!paper?.paper_id) return;
      libraryError.value = "";
      try {
        const response = await fetchWithTimeout(`${API_BASE_URL}/research/papers/${paper.paper_id}`, { method: "GET" });
        libraryPaperDetail.value = await readResponse(response);
        selectedLibraryPaper.value = paper;
      } catch (error) {
        libraryError.value = error.message || "论文详情加载失败，请稍后重试。";
      }
    }

    async function deleteLibraryPaper(paper) {
      if (!paper?.paper_id || !window.confirm(`确定删除《${paper.title}》吗？`)) return;
      libraryError.value = "";
      try {
        const response = await fetchWithTimeout(`${API_BASE_URL}/research/papers/${paper.paper_id}`, { method: "DELETE" });
        if (!response.ok) await readResponse(response);
        if (selectedLibraryPaper.value?.paper_id === paper.paper_id) {
          selectedLibraryPaper.value = null;
          libraryPaperDetail.value = null;
        }
        await loadLibraryPapers();
        ragSelectedPaperIds.value = ragSelectedPaperIds.value.filter((id) => id !== paper.paper_id);
        void loadResearchOverview();
      } catch (error) {
        libraryError.value = error.message || "论文删除失败，请稍后重试。";
      }
    }

    async function analyzeLibraryPaper(paper) {
      if (!paper?.paper_id || libraryAnalysisLoading.value) return;
      libraryAnalysisLoading.value = true;
      libraryError.value = "";
      selectedLibraryPaper.value = paper;
      try {
        const response = await fetchWithTimeout(`${API_BASE_URL}/research/papers/${paper.paper_id}/analyze`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ task: task.value.trim() || DEFAULT_TASK, scenario: scenario.value, role: role.value }),
        });
        result.value = await readResponse(response);
        analysisFromLibrary.value = true;
        selectedReport.value = null;
        saveTaskHistory({
          role: result.value.user_role || role.value,
          roleName: result.value.role_name || selectedRole.value.name,
          task: result.value.user_goal || result.value.user_task || task.value,
          fileName: paper.filename || paper.title || "论文库资料",
          completedAt: new Date().toISOString(),
        });
        taskHistory.value = loadTaskHistory();
        chatMessages.value = [{ role: "assistant", content: "已基于论文库中的资料完成分析。你可以继续针对当前论文提问。" }];
        activeWorkspaceView.value = "assistant";
        void loadResearchOverview();
      } catch (error) {
        libraryError.value = error.message || "论文库分析失败，请稍后重试。";
      } finally {
        libraryAnalysisLoading.value = false;
      }
    }

    function formatLibraryDate(value) {
      const date = new Date(value);
      return Number.isNaN(date.getTime()) ? "时间未知" : date.toLocaleString("zh-CN", { dateStyle: "medium", timeStyle: "short" });
    }

    function formatTextLength(length) {
      return `${Number(length || 0).toLocaleString("zh-CN")} 字`;
    }

    function libraryStatusLabel(status) {
      return {
        uploaded: "等待解析",
        parsed: "已解析",
        indexed: "已建立知识索引",
        failed: "索引失败",
      }[status] || status || "状态未知";
    }

    function applyFullDemo() {
      applyDemo(FULL_DEMO_CASE);
      errorMessage.value = "演示目标已填充。请上传一份可提取文本的 PDF 后开始真实分析。";
    }

    function onFileChange(event) {
      selectedFile.value = event.target.files[0] || null;
      errorMessage.value = "";
    }

    async function readResponse(response, requestToken = null) {
      let data;
      try {
        data = await response.json();
      } catch {
        throw new Error("服务器返回异常，请稍后重试。");
      }
      if (!response.ok) {
        if (response.status === 401) {
          clearIdentitySession(requestToken);
          throw new Error("Session expired. Please sign in again.");
        }
        if (response.status === 403) throw new Error("Permission denied. You do not have access to this Workspace resource.");
        if (response.status === 404) throw new Error("Page or Workspace resource not found.");
        if (response.status === 429) throw new Error("This Workspace is temporarily busy. Please try again shortly.");
        if (response.status === 503) throw new Error("后端服务暂时不可用，请稍后重试。");
        if (response.status >= 500) throw new Error("服务处理失败，请稍后重试。");
        throw new Error("The request could not be completed. Check your input and try again.");
      }
      return data;
    }

    async function fetchWithTimeout(url, options) {
      const controller = new AbortController();
      let timedOut = false;
      const timeout = window.setTimeout(() => {
        timedOut = true;
        controller.abort();
      }, REQUEST_TIMEOUT_MS);

      try {
        const headers = new Headers(options?.headers || {});
        if (sessionToken.value) headers.set("Authorization", `Bearer ${sessionToken.value}`);
        const response = await fetch(url, { ...options, headers, signal: controller.signal });
        if (response.ok) {
          connectionState.value = "CONNECTED";
          connectionMessage.value = "Workspace connected";
        } else if (response.status === 401) {
          connectionState.value = "OFFLINE";
          connectionMessage.value = "Session expired";
        } else if (response.status === 403) {
          connectionState.value = "OFFLINE";
          connectionMessage.value = "Workspace permission denied";
        } else if (response.status === 404) {
          connectionState.value = "OFFLINE";
          connectionMessage.value = "Resource unavailable";
        } else if (response.status >= 500) {
          connectionState.value = "OFFLINE";
          connectionMessage.value = "Service temporarily unavailable";
        }
        return response;
      } catch (error) {
        connectionState.value = "OFFLINE";
        connectionMessage.value = "Workspace offline";
        if (timedOut) throw new Error("Workspace temporarily unavailable. Please reconnect and try again.");
        if (error instanceof TypeError) {
          throw new Error("Workspace temporarily unavailable. Live AI data could not be loaded.");
        }
        throw error;
      } finally {
        window.clearTimeout(timeout);
      }
    }

    async function loadIdentityProfile() {
      const tokenForRequest = sessionToken.value;
      if (!tokenForRequest) { identityProfile.value = null; return false; }
      const requestEpoch = ++identityRequestEpoch;
      try {
        identityRestoreError.value = "";
        const profile = await readResponse(
          await fetchWithTimeout(`${API_BASE_URL}/api/identity/me`),
          tokenForRequest,
        );
        if (requestEpoch !== identityRequestEpoch || tokenForRequest !== sessionToken.value) return false;
        identityProfile.value = profile;
        return true;
      } catch (error) {
        if (requestEpoch !== identityRequestEpoch || tokenForRequest !== sessionToken.value) return false;
        identityRestoreError.value = error.message || "Session expired. Please sign in again.";
        console.error("ResearchOS identity restoration failed.", error);
        clearIdentitySession(tokenForRequest);
        return false;
      }
    }

    function clearIdentitySession(expectedToken = null) {
      if (expectedToken && sessionToken.value !== expectedToken) return false;
      identityRequestEpoch += 1;
      sessionToken.value = "";
      identityProfile.value = null;
      identityMenuOpen.value = false;
      window.localStorage.removeItem("researchos_session_token");
      return true;
    }

    async function initializeAuthorizedWorkspace() {
      if (!identityProfile.value?.workspace?.id) return;
      const workspaceLoaders = [
        ["workspace overview", loadWorkspaceExperience],
        ["missions", loadAIMissions],
        ["knowledge", loadLibraryPapers],
        ["deliveries", loadProductExperience],
        ["research data", loadResearchOsData],
        ["research workspaces", loadResearchWorkspaces],
        ["research overview", loadResearchOverview],
        ["workspace context", loadUnifiedWorkspaceContext],
      ];
      const results = await Promise.allSettled(workspaceLoaders.map(([, load]) => load()));
      results.forEach((result, index) => {
        if (result.status === "rejected") {
          console.error(`ResearchOS workspace initialization failed for ${workspaceLoaders[index][0]}.`, result.reason);
        }
      });
    }

    async function loadUnifiedWorkspaceContext() {
      if (!identityProfile.value?.workspace?.id) return;
      workspaceContextLoading.value = true;
      workspaceContextError.value = "";
      try {
        const [contextResponse, memoryResponse, capabilityResponse] = await Promise.all([
          fetchWithTimeout(`${API_BASE_URL}/api/workspace/context`),
          fetchWithTimeout(`${API_BASE_URL}/api/research-memory`),
          fetchWithTimeout(`${API_BASE_URL}/api/ai-worker/capabilities`),
        ]);
        workspaceContext.value = await readResponse(contextResponse);
        researchMemory.value = await readResponse(memoryResponse);
        aiWorkerCapabilities.value = await readResponse(capabilityResponse);
      } catch (error) {
        workspaceContext.value = null;
        researchMemory.value = [];
        workspaceContextError.value = error.message || "Workspace context is temporarily unavailable.";
      } finally {
        workspaceContextLoading.value = false;
      }
    }

    async function explainResearchMemory(memoryId) {
      if (!memoryId) return;
      researchMemoryActionError.value = "";
      try {
        selectedResearchMemory.value = await readResponse(
          await fetchWithTimeout(`${API_BASE_URL}/api/research-memory/${memoryId}/explain`),
        );
      } catch (error) {
        researchMemoryActionError.value = error.message || "This memory record cannot be opened right now.";
      }
    }

    async function manageResearchMemory(memoryId, action) {
      if (!memoryId || !['validate', 'archive', 'delete'].includes(action)) return;
      researchMemoryActionError.value = "";
      try {
        await readResponse(await fetchWithTimeout(`${API_BASE_URL}/api/research-memory/${memoryId}${action === 'delete' ? '' : `/${action}`}`, {
          method: action === 'delete' ? 'DELETE' : 'POST',
        }));
        if (selectedResearchMemory.value?.id === memoryId) selectedResearchMemory.value = null;
        await loadUnifiedWorkspaceContext();
      } catch (error) {
        researchMemoryActionError.value = error.message || "This memory action could not be completed.";
      }
    }

    async function initializeApplication() {
      const identityRestored = await loadIdentityProfile();
      if (!identityRestored) return;
      void initializeAuthorizedWorkspace();
    }

    async function loginToWorkspace() {
      if (!loginForm.value.email.trim() || !loginForm.value.password) {
        loginError.value = "Enter your email and password.";
        return;
      }
      loginLoading.value = true; loginError.value = "";
      try {
        const response = await fetchWithTimeout(`${API_BASE_URL}/api/identity/sessions`, {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email: loginForm.value.email.trim(), password: loginForm.value.password }),
        });
        const session = await readResponse(response);
        await establishIdentitySession(session);
        loginForm.value.password = "";
      } catch (error) {
        loginError.value = error.message || "Sign-in failed. Please verify your credentials.";
      } finally { loginLoading.value = false; }
    }

    async function establishIdentitySession(session, destination = "dashboard") {
      if (!session?.session_token) throw new Error("Session could not be created. Please try again.");
      identityRequestEpoch += 1;
      sessionToken.value = session.session_token;
      window.localStorage.setItem("researchos_session_token", session.session_token);
      const identityRestored = await loadIdentityProfile();
      if (!identityRestored) {
        console.error("ResearchOS identity verification failed after session creation.");
        throw new Error(identityRestoreError.value || "Session could not be restored. Please sign in again.");
      }
      activeWorkspaceView.value = destination;
      // Identity is the only requirement for entering the Workspace. Individual
      // data modules load independently and show their own empty/error states.
      void initializeAuthorizedWorkspace();
    }

    async function registerWorkspace() {
      const form = registrationForm.value;
      if (!form.name.trim() || !form.email.trim() || !form.password || !form.workspace_name.trim()) {
        loginError.value = "Complete your name, email, password and Workspace name.";
        return;
      }
      loginLoading.value = true; loginError.value = "";
      try {
        const response = await fetchWithTimeout(`${API_BASE_URL}/api/identity/register`, {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ name: form.name.trim(), email: form.email.trim(), password: form.password, workspace_name: form.workspace_name.trim() }),
        });
        await establishIdentitySession(await readResponse(response), "ai-workspace");
        registrationForm.value = { name: "", email: "", password: "", workspace_name: "" };
      } catch (error) {
        loginError.value = error.message || "Workspace creation failed. Please try again.";
      } finally { loginLoading.value = false; }
    }

    async function startDemoSession() {
      demoLoading.value = true; loginError.value = "";
      try {
        const response = await fetchWithTimeout(`${API_BASE_URL}/api/identity/demo-session`, { method: "POST" });
        await establishIdentitySession(await readResponse(response), "dashboard");
      } catch (error) {
        console.error("ResearchOS demo session failed.", error);
        loginError.value = error.message || "Demo Workspace could not be started.";
      } finally { demoLoading.value = false; }
    }

    async function switchIdentityWorkspace(workspaceId) {
      if (!workspaceId || !identityProfile.value) return;
      try {
        await readResponse(await fetchWithTimeout(`${API_BASE_URL}/api/identity/sessions/switch`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ workspace_id: workspaceId }) }));
        await loadIdentityProfile(); await loadAIMissions();
      } catch (error) { aiMissionError.value = error.message || "Workspace switch was not permitted."; }
    }

    async function analyzeDocument() {
      if (loading.value) return;
      if (!selectedFile.value) {
        errorMessage.value = "请先选择一个 PDF 文档。";
        return;
      }
      if (!task.value.trim()) {
        errorMessage.value = "请输入你希望完成的业务目标。";
        return;
      }

      loading.value = true;
      errorMessage.value = "";
      result.value = null;
      analysisFromLibrary.value = false;
      selectedReport.value = null;
      chatMessages.value = [];

      try {
        const formData = new FormData();
        formData.append("file", selectedFile.value);
        formData.append("task", task.value.trim());
        formData.append("scenario", scenario.value);
        formData.append("role", role.value);
        const response = await fetchWithTimeout(`${API_BASE_URL}/agent/analyze-paper`, {
          method: "POST",
          body: formData,
        });
        result.value = await readResponse(response);
        saveTaskHistory({
          role: result.value.user_role || role.value,
          roleName: result.value.role_name || selectedRole.value.name,
          task: result.value.user_goal || result.value.user_task || task.value,
          fileName: selectedFile.value.name,
          completedAt: new Date().toISOString(),
        });
        taskHistory.value = loadTaskHistory();
        chatMessages.value.push({
          role: "assistant",
          content: "文档分析已完成。你可以继续针对当前文档提问。",
        });
      } catch (error) {
        errorMessage.value = error.message || "分析请求失败，请稍后重试。";
      } finally {
        loading.value = false;
      }
    }

    async function askQuestion() {
      const normalizedQuestion = question.value.trim();
      if (!normalizedQuestion || !result.value || asking.value) return;

      asking.value = true;
      errorMessage.value = "";
      chatMessages.value.push({ role: "user", content: normalizedQuestion });
      question.value = "";

      try {
        const response = await fetchWithTimeout(
          `${API_BASE_URL}/agent/papers/${result.value.paper_id}/questions`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ question: normalizedQuestion }),
          },
        );
        const data = await readResponse(response);
        chatMessages.value.push({ role: "assistant", content: data.answer });
      } catch (error) {
        errorMessage.value = error.message || "追问请求失败，请稍后重试。";
        question.value = normalizedQuestion;
      } finally {
        asking.value = false;
      }
    }

    function resetTask() {
      task.value = selectedRole.value.task || DEFAULT_TASK;
    }

    function clearCurrentDocument() {
      selectedFile.value = null;
      result.value = null;
      question.value = "";
      chatMessages.value = [];
      errorMessage.value = "";
      showSimulation.value = false;
      analysisFromLibrary.value = false;
      selectedReport.value = null;
      if (fileInput.value) fileInput.value.value = "";
    }

    // Product UI copy is deliberately resolved at the presentation boundary.
    // It never translates user content, API data, prompts, or evidence; only
    // exact legacy interface labels in the primary English product paths.
    const productCopy = new Map([
      ["主导航", "Primary navigation"],
      ["科研洞察", "Research Intelligence"],
      ["研究任务中心", "Research Mission"],
      ["开始知识问答", "Generate Insight"],
      ["生成结构化报告", "Generate Insight"],
      ["正在生成研究报告…", "Generating insight…"],
      ["刷新论文范围", "Refresh sources"],
      ["刷新中", "Refreshing…"],
      ["刷新列表", "Refresh library"],
      ["＋ 上传 PDF 资料", "Upload PDF"],
      ["正在保存资料…", "Saving material…"],
      ["没有匹配的科研资料", "No matching research material"],
      ["关闭", "Close"],
      ["进入分析", "Open analysis"],
      ["分析中…", "Analyzing…"],
      ["全部状态", "All statuses"],
      ["论文", "Research paper"],
      ["专利", "Patent"],
      ["实验报告", "Experiment report"],
      ["项目资料", "Project material"],
      ["开始协作", "Start mission"],
      ["企业需求分析", "Enterprise solution"],
      ["研究方向探索", "Research discovery"],
      ["实验室知识管理", "Knowledge management"],
      ["分析项目代码", "Analyze project"],
      ["整理论文资料", "Organize research materials"],
      ["优化首页 UI", "Refine home experience"],
      ["只分析", "Analysis only"],
      ["低风险受控执行", "Low-risk controlled execution"],
      ["Evidence 绑定交付", "Evidence-bound delivery"],
      ["尚无可验证资料；不会生成科研结论。", "No verified evidence is available. No research conclusion will be generated."],
      ["尚未检索到可引用 Evidence；不会产生科研结论。", "No traceable evidence has been retrieved. No research conclusion will be generated."],
      ["暂无待确认建议。", "No reviewable suggestions yet."],
      ["尚无 Agent Message。消息仅在实际协作请求、结果、反馈或风险告警发生时记录。", "No collaboration activity has been recorded yet."],
      ["查看全部", "View all"],
      ["继续研究 →", "Continue research →"],
      ["所有入口均标记为 Demo；不会生成假 Evidence、研究结论或未经批准的源码修改。", "Every flow is clearly marked as a demo. It does not create fabricated evidence, research conclusions, or unapproved source changes."],
      ["创建 Organization、设置角色或更新 Policy 后，系统会保存不含 Prompt、CoT 和 Secret 的审计摘要。", "Create an organization, assign a role, or update a policy to record an accountable activity summary."],
      ["不作为 RAG Evidence", "Not used as Knowledge Evidence"],
      ["未识别", "Not identified"],
      ["等待受控执行和人工审核；系统不会自动生成正式交付。", "This mission is waiting for controlled execution and human review. It will not auto-release a deliverable."],
      ["方案已由人工批准。交付包仍会保留 AI Generated Draft 与 NEEDS_CONFIRMATION 标识。", "The plan is approved. Its delivery remains a reviewable AI-generated draft."],
      ["Mission 已完成。所有内容仍为可追溯的 AI 辅助交付草稿。", "This mission is complete. Every output remains a traceable AI-assisted draft."],
      ["暂无待确认建议。", "No reviewable suggestion is waiting."],
      ["暂无持续研究 Workspace", "No active research workspace"],
      ["暂无待确认行动", "No decision is waiting"],
      ["FAILED", "Execution needs attention"],
      ["Failed", "Execution needs attention"],
      ["ERROR", "Execution needs attention"],
      ["Error", "Execution needs attention"],
      ["PENDING", "Preparing"],
      ["PLANNING", "Preparing"],
      ["RUNNING", "Running"],
      ["WAITING_APPROVAL", "Waiting for approval"],
      ["WAITING_REVIEW", "Needs review"],
      ["NEEDS_REVIEW", "Needs review"],
      ["COMPLETED", "Completed"],
      ["STOPPED", "Stopped"],
      ["failed", "Execution needs attention"],
      ["error", "Execution needs attention"],
      ["waiting_approval", "Waiting for approval"],
      ["waiting_review", "Needs review"],
      ["needs_review", "Needs review"],
      ["completed", "Completed"],
      ["executing", "Running"],
      ["planning", "Preparing"],
      ["HUMAN APPROVAL", "RELEASE APPROVAL"],
      ["Patch review", "Change Review"],
      ["Delivery confirmation", "Release approval"],
      ["Execution checkpoint", "Execution progress"],
      ["Live execution events", "Activity updates"],
      ["Auditable action timeline", "Activity updates"],
      ["Environment-aware execution", "Mission progress"],
      ["Computer status", "Current action"],
      ["Plan ready", "Ready to review"],
      ["Generate skill plan", "Prepare execution"],
      ["Start controlled execution", "Begin controlled action"],
      ["Building task plan…", "Preparing action…"],
      ["Executing…", "Working…"],
      ["Environment", "Workspace context"],
      ["Evidence references", "Evidence foundation"],
      ["Controlled tools", "Safety boundaries"],
      ["Code review", "Change review"],
      ["File changed", "Changed material"],
      ["files changed", "materials updated"],
      ["changed lines", "reviewable updates"],
      ["No source change proposed.", "No change is ready for review."],
      ["Retry", "Try again"],
      ["Reject", "Decline"],
      ["输入并探索研究目标", "Frame a research goal"],
      ["创建可审阅研究流程", "Build a reviewable workflow"],
      ["分析项目和受控改动", "Review a project safely"],
      ["刷新中", "Refreshing"],
      ["刷新论文范围", "Refresh research scope"],
      ["暂无可检索论文", "No research papers available"],
      ["暂无持续研究 Workspace", "No active research workspace"],
      ["查看全部", "View all"],
      ["继续研究 →", "Continue research →"],
      ["创建研究任务", "Create research mission"],
      ["推荐研究策略", "Recommend research strategy"],
      ["打开 Workspace", "Open workspace"],
      ["进入 Research", "Open research"],
    ]);
    const productPlaceholders = new Map([
      ["例如：总结这些论文在研究方法上的差异，并说明各自的适用边界。", "What would you like to explore?"],
      ["例如：分析当前 ResearchOS 项目代码，找出前端优化点并生成报告", "Describe the task you want completed"],
      ["例如：RAG 技术路线分析", "For example: RAG technology landscape"],
      ["描述客户需求或研究目标；系统仅基于检索到的真实资料形成 Evidence 引用。", "Describe the customer need or research goal. Only retrieved evidence can be cited."],
    ]);
    let productCopyScheduled = false;
    function applyProductCopy() {
      productCopyScheduled = false;
      const scope = document.querySelector(".app-shell, .login-shell");
      if (!scope) return;
      const walker = document.createTreeWalker(scope, NodeFilter.SHOW_TEXT);
      const replacements = [];
      while (walker.nextNode()) {
        const node = walker.currentNode;
        const value = node.nodeValue.trim();
        if (productCopy.has(value)) replacements.push([node, productCopy.get(value), node.nodeValue]);
      }
      replacements.forEach(([node, replacement, original]) => {
        node.nodeValue = original.replace(original.trim(), replacement);
      });
      scope.querySelectorAll("input[placeholder], textarea[placeholder]").forEach((element) => {
        const replacement = productPlaceholders.get(element.placeholder);
        if (replacement) element.placeholder = replacement;
      });
    }
    const productCopyObserver = new MutationObserver(() => {
      if (!productCopyScheduled) {
        productCopyScheduled = true;
        queueMicrotask(applyProductCopy);
      }
    });
    productCopyObserver.observe(document.body, { childList: true, subtree: true });
    queueMicrotask(applyProductCopy);

    void initializeApplication();

    return {
      agentDecision,
      agentTrace,
      agentWorkflow,
      activeWorkspaceView,
      connectionState,
      connectionMessage,
      identityProfile,
      identityMenuOpen,
      identityRestoreError,
      authMode,
      loginForm,
      registrationForm,
      loginLoading,
      demoLoading,
      loginError,
      currentUser,
      currentWorkspace,
      currentRole,
      loginToWorkspace,
      registerWorkspace,
      startDemoSession,
      clearIdentitySession,
      switchIdentityWorkspace,
      assistantPanelOpen,
      assistantDraft,
      analysisFromLibrary,
      actionCenter,
      askResearchQuestion,
      generateResearchReport,
      showSimulation,
      simulationPrompts,
      analysisData,
      analysisEntries,
      analyzeDocument,
      asking,
      askQuestion,
      chatMessages,
      businessReport,
      clearCurrentDocument,
      decisionReport,
      deliverables,
      demoCases: DEMO_CASES,
      evidenceCards,
      evidenceSources,
      errorMessage,
      libraryAnalysisLoading,
      libraryError,
      librarySearch,
      libraryStatusFilter,
      filteredLibraryPapers,
      knowledgeChunkTotal,
      readyPaperCount,
      libraryFileInput,
      libraryDocumentType,
      libraryLoading,
      libraryStatusLabel,
      libraryPaperDetail,
      libraryPapers,
      libraryUploading,
      fileInput,
      fileSizeLabel,
      formatResultKey,
      loading,
      onFileChange,
      openWorkspaceView,
      question,
      ragAnswer,
      ragAgentPlan,
      ragAgentTrace,
      ragRetrievalEvaluation,
      ragConfidence,
      ragError,
      ragHistory,
      ragHistoryLoading,
      ragLoading,
      ragQuestion,
      ragReportError,
      ragReportLoading,
      ragReportQuality,
      ragReportTrace,
      ragReportEvaluation,
      ragReportConflictReport,
      ragReportResult,
      ragReportSources,
      ragReportTasks: RESEARCH_REPORT_TASKS,
      ragReportType,
      ragSelectedPaperIds,
      ragSelectedSource,
      ragConflictReport,
      ragSourceQuality,
      ragSources,
      reportTitle,
      reportRecords,
      reportDetailLoading,
      reportsError,
      reportsLoading,
      researchOverview,
      researchOsAgents,
      researchOsError,
      researchOsGoal,
      researchOsOverview,
      researchCommandPlan,
      researchOsSections,
      actionableTaskSuggestions,
      agentTimeline,
      aiActivityStream,
      agentTeamCards,
      aiWorkerCapabilities,
      aiWorkerSkills,
      workspaceContext,
      workspaceContextLoading,
      workspaceContextError,
      researchMemory,
      selectedResearchMemory,
      researchMemoryActionError,
      evidenceCenterItems,
      evidenceError,
      evidenceLoading,
      systemStatus,
      systemStatusLoading,
      systemStatusError,
      runtimeStatus,
      runtimeStatusLoading,
      llmRuntimeStatus,
      benchmarkTasks,
      benchmarkDashboard,
      enterpriseScenarios,
      scenarioRunResult,
      scenarioLoading,
      workspaceExperience,
      workspaceExperienceError,
      knowledgeMemory,
      productShowcase,
      workflowDiagnostics,
      agentAnalytics,
      adaptiveAnalytics,
      copilotAnalytics,
      agentMemories,
      diagnosticsLoading,
      diagnosticsError,
      activityLogs,
      demoKnowledgeInitialized,
      visibleDemoKnowledgeAssets,
      researchOsSelectedAgents,
      researchOsTaskLoading,
      researchOsTaskResult,
      workflowPreview,
      workflowLoading,
      workflowError,
      generateResearchWorkflow,
      loadResearchWorkflows,
      executeResearchWorkflow,
      refreshWorkflowRuntime,
      researchWorkspaces,
      selectedResearchWorkspace,
      workspaceQuality,
      workspaceDecisionCandidate,
      workspaceDeliverable,
      workspaceIntelligenceLoading,
      workspaceIntelligenceError,
      workspaceDeliverableLoading,
      workspaceMembers,
      workspaceWorkflow,
      workspaceReviews,
      workspaceEvidenceGraph,
      workspaceReviewLoading,
      autonomousGoal,
      autonomousRun,
      autonomousRuns,
      autonomousTools,
      autonomousMemory,
      autonomousLoading,
      autonomousError,
      workerGoal,
      workerRun,
      workerTools,
      workerTimeline,
      workerLoading,
      workerError,
      workerReviewDecision,
      workerReviewNote,
      operatorGoal,
      operatorTask,
      operatorTasks,
      operatorTools,
      operatorLoading,
      operatorError,
      computerGoal,
      computerTask,
      computerTasks,
      computerTools,
      computerLoading,
      computerPlanLoading,
      computerError,
      computerPlanPreview,
      computerMemory,
      computerEnvironment,
      computerProCatalog,
      computerMode,
      computerAutonomousId,
      fdeSolutions,
      selectedFdeSolution,
      fdeSolutionForm,
      fdeSolutionAnalysis,
      fdeSolutionBlueprint,
      fdeSolutionPackage,
      fdeComputerMissions,
      fdeSolutionLoading,
      fdeSolutionError,
      fdeSolutionReviewNote,
      fdeSolutionVersions,
      aiMissions,
      selectedAIMission,
      aiMissionDashboard,
      aiMissionForm,
      aiMissionLoading,
      aiMissionError,
      aiNotifications,
      aiMissionReviewComment,
      aiMissionRevisionSummary,
      aiMissionDelivery,
      missionArtifacts,
      selectedArtifact,
      artifactLoading,
      artifactError,
      artifactAnalytics,
      connectors,
      connectorAnalytics,
      connectorLoading,
      connectorError,
      connectorForm,
      collaborationAnalytics,
      governance,
      approvalRequests,
      approvalLoading,
      approvalError,
      entryCopilotSession,
      entryCopilotResult,
      entryCopilotLoading,
      enterpriseFiles,
      selectedEnterpriseFile,
      enterpriseFileLoading,
      enterpriseFileError,
      documentAnalytics,
      adaptiveMissionLoading,
      computerMissionTask,
      computerMissionLoading,
      loadFdeSolutions,
      loadFdeSolutionDetail,
      applyFdeSolutionDemo,
      createFdeSolution,
      analyzeFdeSolution,
      generateFdeSolutionBlueprint,
      reviewFdeSolution,
      loadFdeSolutionPackage,
      fdeEvidenceRefs,
      loadAIMissions,
      loadAIMissionDetail,
      loadMissionArtifacts,
      loadApprovalQueue,
      resolveApproval,
      generateMissionArtifact,
      openArtifact,
      reviewArtifact,
      reviseArtifact,
      downloadArtifact,
      loadConnectorCenter,
      registerSqliteConnector,
      loadCollaborationAnalytics,
      loadGovernance,
      loadRuntimeStatus,
      loadLlmRuntimeStatus,
      loadBenchmarks,
      loadScenarios,
      runScenario,
      loadWorkspaceExperience,
      loadUnifiedWorkspaceContext,
      explainResearchMemory,
      manageResearchMemory,
      loadKnowledgeMemory,
      loadProductShowcase,
      createAIMission,
      startCopilotMission,
      loadEnterpriseFiles,
      loadDocumentAnalytics,
      uploadEnterpriseFile,
      openEnterpriseFile,
      createMissionFromDocument,
      runAdaptiveMission,
      reviewAdaptiveMission,
      runAIMission,
      executeAIWorkerRuntime,
      updateMissionControl,
      reviewAIMission,
      reviseAIMission,
      generateAIMissionDelivery,
      startFdeMissionDemo,
      createComputerMission,
      decideComputerMission,
      executeComputerMission,
      markAINotificationRead,
      onboardingState,
      onboardingOpen,
      artifactGallery,
      productDemos,
      completeOnboarding,
      startProductDemo,
      copilotInsight, copilotActions, copilotMemory, copilotLoading, copilotError,
      workspaces,
      activeResearchWorkspace,
      workspaceName,
      workspaceLoading,
      workspaceError,
      researchTasks,
      taskName,
      taskType,
      pendingTaskProject,
      taskCenterLoading,
      agentMonitor,
      deliveryPreview,
      deliveryLoading,
      fdeStageIndex,
      fdeTaskStatuses,
      fdeAcceptanceReady,
      fdeDemoStep,
      fdeArchitectureSelection,
      fdeArchitectureDescriptions,
      fdeClientType,
      fdeSelectedNeeds,
      fdeConfigurationResult,
      fdeProblemInput,
      fdeDiagnosisResult,
      fdeDeliveryScenario,
      fdeDeliveryReport,
      fdeScenarioOptions,
      fdeScenarioProfile,
      solutionScenarios,
      selectedSolutionScenario,
      solutionBlueprint,
      solutionRoi,
      solutionAdminOverview,
      solutionDeliveryReport,
      solutionDemoFlow,
      solutionLoading,
      solutionError,
      solutionDemoStep,
      enterpriseOrganization, enterpriseMembers, enterpriseProjects, enterpriseActivity, enterpriseDashboard, enterpriseKnowledge,
      enterpriseLoading, enterpriseError, enterpriseOrgName, enterpriseAdminName, enterpriseProjectName, enterpriseProjectGoal,
      enterpriseMeetingNotes, enterpriseMeeting, enterpriseDeliveryPackage, createEnterpriseOrganization, createEnterpriseProject, createEnterpriseMeeting, loadEnterpriseDeliveryPackage,
      loadEnterpriseHub,
      implementationRisks,
      researchBi,
      researchBiLoading,
      researchProjects,
      projectError,
      projectForm,
      pendingProjectActionId,
      projectLoading,
      projectMatchResult,
      projectMatching,
      researchActions,
      researchDecisions,
      actionLoading,
      actionError,
      decisionNotes,
      selectedOutcomeProjectId,
      projectOutcomes,
      outcomeLoading,
      outcomeError,
      outcomeForm,
      valueAssessment,
      valueAssessmentLoading,
      labProfile,
      labProfileLoading,
      documentTypeLabel,
      knowledgeAssetSummary,
      knowledgeAssetAgents,
      advisorAudience,
      advisorRoles,
      demoStarted,
      demoSteps,
      applyResearchOsDemo,
      applyFdeDeliveryDemo,
      startDemoMode,
      openDemoStep,
      projectDeliveryStage,
      selectAdvisorScenario,
      assessResearchValue,
      createResearchProject,
      prepareTaskFromProject,
      loadResearchBi,
      loadResearchProjects,
      loadResearchActions,
      decisionForAction,
      actionTitle,
      createActionFromSuggestion,
      updateResearchAction,
      recordResearchDecision,
      prepareProjectFromDecision,
      loadProjectOutcomes,
      createProjectOutcome,
      updateProjectOutcome,
      updateOutcomeKnowledgeStatus,
      deleteProjectOutcome,
      runProjectMatch,
      generateLabProfile,
      loadEvidenceCenter,
      loadSystemStatus,
      loadWorkflowDiagnostics,
      loadAgentAnalytics,
      loadCopilotAnalytics,
      loadAgentMemories,
      deleteAgentMemory,
      initializeDemoKnowledge,
      runResearchOsTask,
      loadResearchWorkspaces,
      loadResearchWorkspaceDetails,
      generateWorkspaceDeliverable,
      reviewWorkspaceItem,
      generateResearchBrief,
      applyResearchWorkspaceDemo,
      researchTimelineLabel,
      runAutonomousResearch,
      loadAutonomousWorkspace,
      runResearchWorker,
      loadResearchWorkerWorkspace,
      loadOperatorStudio,
      runOperatorTask,
      applyOperatorTemplate,
      reviewOperatorTask,
      loadComputerStudio,
      previewComputerPlan,
      loadCopilotCenter, createCopilotSuggestion, reviewCopilotAction,
      runComputerTask,
      applyComputerTemplate,
      reviewComputerAction,
      applyWorkerTemplate,
      applyWorkerDemo,
      reviewResearchWorker,
      loadEnterpriseWorkspace,
      createResearchWorkspace,
      loadResearchTasks,
      createResearchTask,
      loadAgentMonitor,
      loadClientDelivery,
      exportClientDelivery,
      openFdeDeliveryRehearsal,
      advanceFdeStage,
      startFdeSolutionDemo,
      nextFdeDemoStep,
      previousFdeDemoStep,
      toggleFdeNeed,
      generateFdeConfiguration,
      diagnoseFdeProblem,
      generateFdeDeliveryReport,
      selectFdeDeliveryScenario,
      loadSolutionDelivery,
      selectSolutionScenario,
      startSolutionDemo,
      beginResearchFromHome,
      sendAssistantToResearch,
      resumeResearchWorkspace,
      toggleResearchOsAgent,
      overviewLoading,
      resetTask,
      result,
      scenario,
      scenarioOptions: SCENARIO_OPTIONS,
      role,
      roleOptions: ROLE_OPTIONS,
      selectedRole,
      selectRole,
      applyDemo,
      applyFullDemo,
      selectedFile,
      selectedLibraryPaper,
      selectedReport,
      selectedScenario,
      roleHistory,
      quickWorkspaceTasks: QUICK_WORKSPACE_TASKS,
      selectedQuickTask,
      selectQuickTask,
      task,
      analyzeLibraryPaper,
      deleteLibraryPaper,
      formatLibraryDate,
      formatTextLength,
      loadLibraryPapers,
      loadResearchOverview,
      loadResearchReports,
      loadRagHistory,
      qualityCheck,
      trustReport,
      uploadStatus,
      valueEstimation,
      uploadLibraryPaper,
      viewLibraryPaper,
      viewResearchReport,
      restoreRagHistory,
      showRagSource,
    };
  },
  template: `
    <main v-if="identityProfile" class="app-shell">
      <header class="workspace-header">
        <nav class="top-navigation" aria-label="主导航">
           <button class="brand-button" type="button" @click="openWorkspaceView('dashboard')"><span class="brand-orb" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none"><path d="M12 2.8 14.4 9.6 21.2 12l-6.8 2.4L12 21.2l-2.4-6.8L2.8 12l6.8-2.4L12 2.8Z" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"/></svg></span><span><b>ResearchOS</b><small>AI Research Workspace</small></span></button>
          <div class="top-navigation-links product-navigation">
            <button type="button" :class="{ active: activeWorkspaceView === 'dashboard' }" @click="openWorkspaceView('dashboard')">Home</button>
            <button type="button" :class="{ active: activeWorkspaceView === 'mission-center' || activeWorkspaceView === 'team-workspace' }" @click="openWorkspaceView('mission-center')">Missions</button>
            <button type="button" :class="{ active: activeWorkspaceView === 'knowledge' || activeWorkspaceView === 'insights' || activeWorkspaceView === 'evidence' }" @click="openWorkspaceView('knowledge')">Knowledge</button>
            <button type="button" :class="{ active: activeWorkspaceView === 'artifact-center' }" @click="openWorkspaceView('artifact-center')">Deliveries</button>
            <button type="button" :class="{ active: activeWorkspaceView === 'computer' }" @click="openWorkspaceView('computer')">Computer</button>
            <span class="navigation-contract-marker" aria-hidden="true">Workspace</span>
          </div>
         <div class="nav-utilities"><label v-if="identityProfile?.workspaces?.length" class="workspace-context-selector"><span>Workspace</span><select :value="identityProfile.workspace.id" aria-label="Switch workspace" @change="switchIdentityWorkspace($event.target.value)"><option v-for="workspace in identityProfile.workspaces" :key="workspace.id" :value="workspace.id">{{ workspace.name }}</option></select><small>{{ identityProfile.workspace.role }} · {{ workspaceExperience?.missions?.[0]?.title || 'No active mission' }}</small></label><button v-if="['OWNER','ADMIN'].includes(identityProfile?.workspace?.role)" class="system-link" type="button" :class="{ active: ['governance','system','benchmarks'].includes(activeWorkspaceView) }" @click="openWorkspaceView('governance')">Admin Console</button><button class="demo-mode-button" type="button" @click="openWorkspaceView('demo-center')">Demo</button><span class="top-navigation-status"><i></i> Ready</span><div class="identity-menu"><button class="user-avatar" type="button" aria-label="当前工作空间用户" @click="identityMenuOpen = !identityMenuOpen">{{ identityProfile?.user?.display_name?.slice(0, 1) || '•' }}</button><section v-if="identityMenuOpen" class="identity-profile-menu"><b>{{ identityProfile?.user?.display_name || 'No active user' }}</b><small>{{ identityProfile ? (identityProfile.workspace.name + ' · ' + identityProfile.workspace.role) : 'Sign in to an authorized Workspace to access enterprise resources.' }}</small><button v-if="identityProfile?.workspace?.role === 'OWNER' || identityProfile?.workspace?.role === 'ADMIN'" class="text-button" type="button" @click="openWorkspaceView('governance')">Open Admin Console</button></section></div></div>
        </nav>
      </header>

      <button class="connection-status" :class="connectionState.toLowerCase()" type="button" aria-live="polite" @click="openWorkspaceView(activeWorkspaceView)">
        <i></i><span>{{ connectionMessage }}</span>
      </button>

      <section v-if="currentWorkspace?.is_demo" class="demo-workspace-banner" aria-label="Demo Workspace notice">
        <span>DEMO</span><div><b>ResearchOS Demo Environment</b><small>This Workspace is for demonstration only. Customer data and Admin Console are unavailable.</small></div>
      </section>

      <section v-if="activeWorkspaceView === 'dashboard'" class="home-workspace" aria-label="ResearchOS Home">
          <div class="home-hero workspace-home-hero"><p class="section-kicker">RESEARCHOS · EVIDENCE-DRIVEN AI WORKSPACE</p><h1>Your AI Worker<br />is ready to work.</h1><p>Transform research goals into evidence-backed decisions and enterprise deliverables.</p><div class="home-research-input"><textarea v-model="researchOsGoal" rows="3" aria-label="Describe your research goal or task" placeholder="Describe your research or business goal..."></textarea><button type="button" class="primary-card-action" :disabled="entryCopilotLoading" @click="startCopilotMission">{{ entryCopilotLoading ? 'Planning mission…' : 'Start Mission' }}</button></div><div class="enterprise-upload-strip"><button class="outline-button" type="button" @click="openWorkspaceView('demo-center')">Try Demo</button><label class="outline-button"><input type="file" accept=".pdf,.docx,.xlsx,.pptx,.png,.jpg,.jpeg,.txt" @change="uploadEnterpriseFile" hidden />{{ enterpriseFileLoading ? 'Analyzing material…' : 'Add material' }}</label></div><small>AI drafts remain reviewable. Customer material never becomes Knowledge Evidence automatically.</small><p v-if="entryCopilotResult" class="quiet-note">{{ entryCopilotResult.summary }} · Mission 已创建。</p><p v-if="enterpriseFileError" class="error-alert"><span>!</span>{{ enterpriseFileError }}</p></div>
          <div class="home-quick-grid product-capability-grid" aria-label="AI Worker capabilities"><button type="button" @click="beginResearchFromHome('Analyze the indexed research materials and prepare an evidence-backed research workflow.')"><span class="capability-mark">01</span><b>Research Intelligence</b><small>Discover insights from trusted evidence.</small></button><button type="button" @click="openWorkspaceView('computer'); computerGoal = 'Review my project code'; computerPlanPreview = null"><span class="capability-mark">02</span><b>Controlled Computer</b><small>Execute approved digital workflows safely.</small></button><button type="button" @click="openWorkspaceView('artifact-center')"><span class="capability-mark">03</span><b>Enterprise Delivery</b><small>Generate reviewed business artifacts.</small></button></div>
          <section class="home-focus-grid home-missions-panel" :class="'connection-' + connectionState.toLowerCase()" aria-label="Active missions">
            <article class="home-focus-card">
              <header><span class="focus-dot mission-dot"></span><p class="section-kicker">ACTIVE MISSIONS</p></header>
              <template v-if="connectionState === 'CONNECTING'"><div class="home-card-skeleton"><i></i><i></i><i></i></div></template>
              <template v-else-if="connectionState === 'OFFLINE'"><div class="home-offline-state"><span>✦</span><h3>No live missions yet</h3><p>Workspace connection is required to load your AI workflows.</p><button class="secondary-card-action" type="button" @click="openWorkspaceView(activeWorkspaceView)">Retry connection</button></div></template>
              <template v-else-if="workspaceExperience?.missions?.length"><div v-for="item in workspaceExperience.missions.slice(0,2)" :key="item.id" class="focus-item"><b>{{ item.title }}</b><small>{{ item.current_step || item.status }}</small></div><button class="text-button" type="button" @click="openWorkspaceView('mission-center')">Open missions →</button></template>
              <template v-else><div class="home-empty-action"><h3>Start a focused mission</h3><p>Describe an outcome above and your AI Worker will prepare a reviewable workflow.</p><button class="text-button" type="button" @click="researchOsGoal = 'Analyze the indexed research materials and prepare an evidence-backed workflow.'">Use an example →</button></div></template>
            </article>
            <article class="home-focus-card"><header><span class="focus-dot evidence-dot"></span><p class="section-kicker">EVIDENCE STATUS</p></header><template v-if="selectedAIMission?.evidence_refs?.length"><h3>{{ selectedAIMission.evidence_refs.length }} traceable references in focus</h3><p>Only validated Evidence can support research insights and delivery drafts.</p><button class="text-button" type="button" @click="openWorkspaceView('mission-center')">Review evidence →</button></template><template v-else><h3>Evidence waiting for a mission</h3><p>AI will never turn source candidates into research conclusions automatically.</p><button class="text-button" type="button" @click="beginResearchFromHome('Analyze the indexed research materials and prepare an evidence-backed workflow.')">Start research →</button></template></article>
            <article class="home-focus-card"><header><span class="focus-dot review-dot"></span><p class="section-kicker">REVIEW QUEUE</p></header><template v-if="approvalRequests.filter(request => request.status === 'PENDING').length"><h3>{{ approvalRequests.filter(request => request.status === 'PENDING').length }} decisions need attention</h3><p>Evidence, controlled actions and deliverables stay pending until an authorized human reviews them.</p><button class="text-button" type="button" @click="openWorkspaceView('mission-center')">Open review queue →</button></template><template v-else><h3>No decisions waiting</h3><p>Your next reviewed Evidence or delivery release will appear here.</p><button class="text-button" type="button" @click="openWorkspaceView('artifact-center')">View deliveries →</button></template></article>
          </section>
        <section class="home-recent-workspaces"><header><div><p class="section-kicker">RECENT WORKSPACES</p><h3>继续正在进行的研究</h3></div><button class="text-button" type="button" @click="openWorkspaceView('research-workspace')">查看全部</button></header><div v-if="researchWorkspaces.length" class="recent-workspace-grid"><article v-for="item in researchWorkspaces.slice(0,3)" :key="item.workspace_id"><span>{{ item.strategy_type || 'research' }}</span><h4>{{ item.title }}</h4><p><b>{{ item.status || 'created' }}</b> · {{ item.human_review_required ? 'Review Pending' : 'Review not required' }}</p><small>Evidence：{{ item.evidence_count || 0 }}</small><button type="button" @click="resumeResearchWorkspace(item)">继续研究 →</button></article></div><div v-else class="home-empty-state"><b>暂无持续研究 Workspace</b><span>提交一项有依据的研究任务后，系统会保存策略、Evidence 和审核状态。</span></div></section>
      </section>

      <section v-if="activeWorkspaceView === 'document-intelligence'" class="document-intelligence-center" aria-label="Document Intelligence">
        <header class="dashboard-heading"><div><p class="section-kicker">ENTERPRISE INPUT LAYER</p><h2>Document Intelligence</h2><p>将客户提供的资料解析为可确认需求，再创建可审阅 Mission。客户材料不会伪装为知识库 Evidence。</p></div><label class="primary-card-action"><input type="file" accept=".pdf,.docx,.xlsx,.pptx,.png,.jpg,.jpeg,.txt,.py,.js,.ts,.tsx,.jsx,.java,.c,.cpp,.cs,.go,.rs,.sql,.html,.css,.json,.yaml,.yml" @change="uploadEnterpriseFile" hidden />{{ enterpriseFileLoading ? 'Analyzing…' : 'Upload file' }}</label></header>
        <p v-if="enterpriseFileError" class="error-alert"><span>!</span>{{ enterpriseFileError }}</p>
        <div class="document-intelligence-layout"><aside><p class="section-kicker">CUSTOMER MATERIAL</p><button v-for="file in enterpriseFiles" :key="file.id" type="button" :class="{ active: selectedEnterpriseFile?.id === file.id }" @click="openEnterpriseFile(file.id)"><b>{{ file.filename }}</b><small>{{ file.file_type }} · {{ file.status }}</small></button><p v-if="!enterpriseFiles.length" class="quiet-note">尚无客户资料。上传后才会出现解析结果。</p></aside><main v-if="selectedEnterpriseFile"><section class="document-summary-card"><span>{{ selectedEnterpriseFile.classification }}</span><h3>{{ selectedEnterpriseFile.filename }}</h3><p>{{ selectedEnterpriseFile.summary?.summary }}</p><small>{{ selectedEnterpriseFile.summary?.limitations }}</small></section><section class="document-analysis-card"><p class="section-kicker">EXTRACTED REQUIREMENTS</p><h3>所有识别项均待客户确认</h3><article v-for="item in selectedEnterpriseFile.requirements || []" :key="item.id"><b>{{ item.category }}</b><p>{{ item.description }}</p><small>{{ item.status }}</small></article><p v-if="!(selectedEnterpriseFile.requirements || []).length" class="quiet-note">资料不足以生成需求草稿；请补充可解析内容。</p></section><footer class="document-mission-action"><div><b>Human confirmation required</b><p>确认后将通过 Copilot 创建现有 Mission 与 Planner Graph，并关联此客户材料。</p></div><button class="primary-card-action" type="button" :disabled="enterpriseFileLoading || selectedEnterpriseFile.status !== 'COMPLETED'" @click="createMissionFromDocument">Confirm requirements & create Mission</button></footer></main><main v-else class="document-empty-state"><b>Upload a customer document</b><p>支持 PDF、DOCX、XLSX、PPTX、图片、文本和安全代码文件。</p></main></div>
      </section>

      <section v-if="activeWorkspaceView === 'mission-center'" class="mission-center mission-collaboration-workspace" aria-label="AI Worker Workflow">
        <header class="dashboard-heading"><div><p class="section-kicker">MISSION WORKSPACE</p><h2>{{ selectedAIMission?.title || 'Create an evidence-driven mission.' }}</h2><p>{{ selectedAIMission ? ((selectedAIMission.status || 'PLANNING') + ' · ' + (selectedAIMission.owner || 'Workspace owner') + ' · ' + (selectedAIMission.created_at || 'Created in this Workspace')) : 'Create a mission to turn a customer need into a reviewable deliverable.' }}</p></div><div class="mission-header-actions"><button class="outline-button" type="button" :disabled="aiMissionLoading" @click="startFdeMissionDemo">Start FDE Demo</button><button class="outline-button" type="button" :disabled="aiMissionLoading" @click="loadAIMissions">Refresh</button></div></header>
        <ol class="mission-stage-strip" aria-label="Mission stages"><li :class="{ active: !!selectedAIMission }"><span>01</span><b>Understand</b><small>Goal confirmed</small></li><li :class="{ active: ['RUNNING','WAITING_REVIEW','APPROVED','COMPLETED'].includes(selectedAIMission?.status) }"><span>02</span><b>Research</b><small>Evidence gathered</small></li><li :class="{ active: ['WAITING_REVIEW','APPROVED','COMPLETED'].includes(selectedAIMission?.status) }"><span>03</span><b>Review</b><small>Human decision</small></li><li :class="{ active: ['COMPLETED'].includes(selectedAIMission?.status) }"><span>04</span><b>Deliver</b><small>Output ready</small></li></ol>
        <p v-if="aiMissionError" class="error-alert"><span>!</span>{{ aiMissionError }}</p>
        <div class="mission-center-layout"><section class="mission-create-surface"><p class="section-kicker">CREATE MISSION</p><label>Mission title<input v-model="aiMissionForm.title" placeholder="例如：RAG 技术路线分析" /></label><label>Mission type<select v-model="aiMissionForm.mission_type"><option>RESEARCH</option><option>SOLUTION</option><option>DELIVERY</option></select></label><label>Customer need / Goal<textarea v-model="aiMissionForm.goal" rows="5" placeholder="描述客户需求或研究目标；系统仅基于检索到的真实资料形成 Evidence 引用。"></textarea></label><button class="primary-card-action" type="button" :disabled="aiMissionLoading" @click="createAIMission">Create AI Mission</button></section>
          <section class="mission-stream-surface"><template v-if="selectedAIMission"><header><div><p class="section-kicker">AI WORKER WORKFLOW</p><h3>{{ selectedAIMission.title }}</h3><small>{{ selectedAIMission.worker_contract?.status || selectedAIMission.status }} · {{ selectedAIMission.progress }}% · {{ selectedAIMission.current_step }}</small></div><button v-if="['PLANNING','NEEDS_REVISION'].includes(selectedAIMission.status)" class="primary-card-action" type="button" :disabled="aiMissionLoading" @click="runAIMission(selectedAIMission.id)">Run AI Worker</button></header><section class="mission-requirements"><span>MISSION CONTRACT</span><p>{{ selectedAIMission.worker_contract?.objective || selectedAIMission.goal }}</p><small>Evidence · {{ selectedAIMission.worker_contract?.evidence_requirement || 'TRACEABLE_EVIDENCE_REQUIRED' }} · Approval · {{ selectedAIMission.worker_contract?.approval_requirement || 'HUMAN_REVIEW_REQUIRED' }}</small></section><ol class="mission-timeline"><li v-for="item in selectedAIMission.timeline || []" :key="item.id"><b>AI Worker</b><div><strong>{{ item.action }}</strong><p>{{ item.result }}</p><small>Evidence: {{ item.evidence_count }} · {{ item.status }} · {{ item.created_at }}</small></div></li></ol><section class="mission-evidence-list"><span>REAL EVIDENCE REFERENCES</span><div v-for="item in selectedAIMission.evidence_refs || []" :key="item.chunk_id"><b>{{ item.source }}</b><small>{{ item.paper_id }} / {{ item.chunk_id }} · {{ item.section }}</small></div><p v-if="!(selectedAIMission.evidence_refs || []).length">尚未检索到可引用 Evidence；不会产生科研结论。</p></section><section class="mission-graph"><span>EVIDENCE GRAPH</span><div v-for="node in selectedAIMission.evidence_graph?.nodes || []" :key="node.id"><b>{{ node.type }}</b><small>{{ node.label }}</small></div><p>{{ selectedAIMission.evidence_graph?.boundary }}</p></section><section class="mission-review-panel"><span>HUMAN REVIEW</span><template v-if="selectedAIMission.status === 'WAITING_REVIEW'"><textarea v-model="aiMissionReviewComment" rows="3" placeholder="记录审核意见（可选）"></textarea><div><button class="primary-card-action" type="button" :disabled="aiMissionLoading" @click="reviewAIMission('APPROVED')">Approve</button><button class="outline-button" type="button" :disabled="aiMissionLoading" @click="reviewAIMission('NEEDS_REVISION')">Needs revision</button><button class="text-button" type="button" :disabled="aiMissionLoading" @click="reviewAIMission('REJECTED')">Reject</button></div></template><template v-else-if="selectedAIMission.status === 'NEEDS_REVISION'"><textarea v-model="aiMissionRevisionSummary" rows="3" placeholder="说明版本修订要求"></textarea><button class="primary-card-action" type="button" :disabled="aiMissionLoading" @click="reviseAIMission">Create revised draft</button></template><template v-else-if="selectedAIMission.status === 'APPROVED'"><p>方案已由人工批准。交付包仍会保留 AI Generated Draft 与 NEEDS_CONFIRMATION 标识。</p><button class="primary-card-action" type="button" :disabled="aiMissionLoading" @click="generateAIMissionDelivery">Generate Delivery Package</button></template><template v-else-if="selectedAIMission.status === 'COMPLETED'"><p>Mission 已完成。所有内容仍为可追溯的 AI 辅助交付草稿。</p></template><p v-else>等待受控执行和人工审核；系统不会自动生成正式交付。</p></section><section v-if="aiMissionDelivery" class="mission-delivery-package"><span>DELIVERY PACKAGE</span><b>{{ aiMissionDelivery.label }}</b><p>{{ aiMissionDelivery.executive_summary }}</p><small>Evidence references: {{ aiMissionDelivery.evidence_references?.length || 0 }}</small></section></template><div v-else class="product-empty-state"><b>No mission selected</b><p>Create or choose an AI Worker mission to inspect its auditable workflow.</p></div></section>
          <aside class="mission-intelligence-surface"><p class="section-kicker">AI WORKER CAPABILITIES</p><article v-for="skill in selectedAIMission?.worker_contract?.available_skills || aiWorkerSkills" :key="skill.id"><b>{{ skill.name }}</b><span>{{ skill.evidence_required ? 'Evidence aware' : skill.approval_required ? 'Approval gated' : 'Available' }}</span><small>{{ skill.description }}</small></article><p v-if="!(selectedAIMission?.worker_contract?.available_skills || aiWorkerSkills).length" class="quiet-note">Loading approved AI Worker capabilities.</p><p class="section-kicker">NOTIFICATIONS</p><button v-for="item in aiNotifications" :key="item.id" class="mission-notification" :class="{ read: item.read }" type="button" @click="markAINotificationRead(item.id)"><b>{{ item.type }}</b><small>{{ item.message }}</small></button><p v-if="!aiNotifications.length" class="quiet-note">No persisted notifications.</p></aside>
        </div>
        <section v-if="selectedAIMission" class="mission-version-history"><span>VERSION HISTORY</span><div v-for="item in selectedAIMission.versions || []" :key="item.id"><b>v{{ item.version }} · {{ item.status }}</b><small>{{ item.created_by }} · {{ item.change_summary }} · {{ item.created_at }}</small></div><p v-if="!(selectedAIMission.versions || []).length">尚未生成 Blueprint 版本。</p></section>
        <section class="mission-tool-trace approval-queue" aria-label="Workspace Review Queue"><header><div><p class="section-kicker">WORKSPACE REVIEW QUEUE</p><h3>Pending reviews</h3><p>Evidence, artifacts, controlled computer actions and decisions remain pending until an authorized human resolves them.</p></div><button class="outline-button" type="button" :disabled="approvalLoading" @click="loadApprovalQueue">{{ approvalLoading ? 'Refreshing…' : 'Refresh queue' }}</button></header><p v-if="approvalError" class="quiet-note">{{ approvalError }}</p><article v-for="item in approvalRequests.filter(request => request.status === 'PENDING')" :key="item.id"><div><b>{{ item.request_type }}</b><small>{{ item.priority }} priority · Mission {{ item.mission_id || 'Workspace resource' }}</small><p>{{ item.comment || 'Human review requested for this Workspace resource.' }}</p></div><footer v-if="['OWNER','ADMIN','MANAGER','REVIEWER'].includes(identityProfile?.workspace?.role)"><button class="primary-card-action" type="button" :disabled="approvalLoading" @click="resolveApproval(item, 'approve')">Approve</button><button class="outline-button" type="button" :disabled="approvalLoading" @click="resolveApproval(item, 'changes')">Request changes</button><button class="text-button" type="button" :disabled="approvalLoading" @click="resolveApproval(item, 'reject')">Reject</button></footer></article><div v-if="!approvalLoading && !approvalRequests.filter(request => request.status === 'PENDING').length" class="product-empty-state"><b>Nothing waiting for review</b><p>Reviewable Evidence, delivery releases and controlled Computer actions will appear here when an approved workflow requests a human decision.</p></div></section>
        <section v-if="selectedAIMission?.evaluation" class="mission-evaluation-card"><span>WORKER QUALITY CHECK</span><b>Quality check · {{ selectedAIMission.evaluation.evaluation_score }}/100</b><small>Evidence {{ selectedAIMission.evaluation.evidence_coverage }} · Verification {{ selectedAIMission.evaluation.verification_result }} · Human revisions {{ selectedAIMission.evaluation.human_revision_count }} · Safety {{ selectedAIMission.evaluation.execution_safety }}</small><p v-if="selectedAIMission.evaluation.failure_type">{{ selectedAIMission.evaluation.failure_type }} · {{ selectedAIMission.evaluation.failure_reason }}</p><details v-if="selectedAIMission.agent_traces?.length"><summary>Workflow details</summary><div v-for="trace in selectedAIMission.agent_traces" :key="trace.created_at + trace.action"><b>AI Worker</b><small>{{ trace.action }} · {{ trace.evidence_count }} Evidence · {{ trace.status }}</small><p>{{ trace.output_summary }}</p></div></details></section>
        <section v-if="selectedAIMission?.planner_plan" class="mission-evaluation-card"><span>AI WORKER PLAN</span><b>Approved skill workflow</b><p>{{ selectedAIMission.planner_plan.reason_summary }}</p><div class="planner-agent-list"><small v-for="skill in selectedAIMission.worker_contract?.available_skills || aiWorkerSkills" :key="skill.id">✓ {{ skill.name }}</small></div><ol class="mission-timeline"><li v-for="node in selectedAIMission.planner_plan.execution_graph" :key="node.id"><b>{{ node.order }}</b><div><strong>AI Worker</strong><p>{{ node.node_name }}</p><small>{{ node.status }} · depends on {{ node.depends_on?.join(', ') || 'start' }}</small></div></li></ol></section>
        <section v-if="selectedAIMission" class="mission-evaluation-card"><span>AI WORKER DECISION CYCLE</span><b>Cycle {{ selectedAIMission.adaptive_iterations?.length || 0 }} / 3</b><p>每次仅执行一个可审计决策；Evidence 不足只请求现有 RAG，Computer Skill 变更始终需要重新审批。</p><button v-if="!['WAITING_ADAPTIVE_REVIEW','COMPLETED','FAILED'].includes(selectedAIMission.status)" class="outline-button" type="button" :disabled="adaptiveMissionLoading" @click="runAdaptiveMission">{{ adaptiveMissionLoading ? 'Evaluating…' : 'Evaluate next step' }}</button><div v-if="selectedAIMission.status === 'WAITING_ADAPTIVE_REVIEW'"><button class="primary-card-action" type="button" :disabled="adaptiveMissionLoading" @click="reviewAdaptiveMission('APPROVE')">Approve next step</button><button class="text-button" type="button" :disabled="adaptiveMissionLoading" @click="reviewAdaptiveMission('REJECT')">Reject</button><button class="outline-button" type="button" :disabled="adaptiveMissionLoading" @click="reviewAdaptiveMission('NEEDS_REVISION')">Needs revision</button></div><ol class="mission-timeline"><li v-for="item in selectedAIMission.adaptive_iterations || []" :key="item.created_at + item.iteration"><b>{{ item.iteration }}</b><div><strong>{{ item.decision }}</strong><p>{{ item.summary }}</p><small>{{ item.trigger }}</small></div></li></ol></section>
        <section v-if="selectedAIMission" class="computer-mission-center"><header><div><span>CONTROLLED COMPUTER WORKSPACE</span><b>Observe · Plan · Approval · Execute · Verify</b></div><small>仅允许当前 ResearchOS 项目的白名单文件与固定验证命令；没有真实视觉输入时会明确标记为 Demo only。</small></header><div class="computer-mission-create"><input v-model="computerMissionTask" placeholder="例如：为首页输入区准备可审阅的焦点状态优化" /><button class="outline-button" type="button" :disabled="computerMissionLoading" @click="createComputerMission">Create & Analyze</button></div><article v-for="item in selectedAIMission.computer_missions || []" :key="item.id"><div class="computer-mission-summary"><b>{{ item.task }}</b><small>{{ item.status }} · {{ item.approval_status }} · {{ item.risk_level }} risk</small><ol class="computer-control-timeline"><li :class="{ complete: item.workspace?.status || item.action_plan?.computer_observation }"><span>01</span><b>Observation</b><small>{{ item.action_plan?.computer_observation?.vision_mode === 'demo_only' ? 'Demo-only metadata observation' : 'Waiting for controlled observation' }}</small></li><li :class="{ complete: item.action_plan?.controlled_action }"><span>02</span><b>Planning</b><small>{{ item.action_plan?.controlled_action?.action_type || 'No action selected' }}</small></li><li :class="{ active: item.status === 'WAITING_APPROVAL', complete: item.approval_status === 'APPROVED' }"><span>03</span><b>Approval</b><small>{{ item.approval_status || 'Pending' }}</small></li><li :class="{ complete: ['EXECUTING','VERIFYING','COMPLETED','NEEDS_REVISION'].includes(item.status) }"><span>04</span><b>Execution</b><small>Controlled only</small></li><li :class="{ complete: item.verification?.controlled_verification?.status === 'SUCCESS', active: item.status === 'VERIFYING' }"><span>05</span><b>Verification</b><small>{{ item.verification?.controlled_verification?.status || 'Pending' }}</small></li></ol><details><summary>View approved Diff & verification</summary><p>Workspace: {{ item.workspace?.boundary || '尚未扫描' }}</p><p>Plan: {{ item.action_plan?.steps?.length || 0 }} reviewable steps · verification {{ item.verification?.status || 'PENDING' }}</p><pre v-if="item.diff_content">{{ item.diff_content }}</pre><p v-else>尚未生成可安全执行的 Diff。</p><small v-if="item.execution_log?.length">{{ item.execution_log[item.execution_log.length - 1].action }} · {{ item.execution_log[item.execution_log.length - 1].status }}</small></details></div><div class="computer-mission-actions"><button v-if="item.status === 'WAITING_APPROVAL'" class="primary-card-action" type="button" :disabled="computerMissionLoading" @click="decideComputerMission(item, 'APPROVED')">Approve Diff</button><button v-if="item.status === 'WAITING_APPROVAL'" class="text-button" type="button" :disabled="computerMissionLoading" @click="decideComputerMission(item, 'REJECTED')">Reject</button><button v-if="item.status === 'WAITING_APPROVAL'" class="outline-button" type="button" :disabled="computerMissionLoading" @click="decideComputerMission(item, 'NEEDS_REVISION')">Request Revision</button><button v-if="item.status === 'APPROVED' && item.execution_allowed" class="primary-card-action" type="button" :disabled="computerMissionLoading" @click="executeComputerMission(item)">Execute Approved Diff</button></div></article><p v-if="!(selectedAIMission.computer_missions || []).length">尚无 Computer Mission。创建后只扫描受控 Workspace 与生成 Diff，不会自动写入文件。</p></section>
        <section v-if="selectedAIMission" class="computer-execution-runtime" aria-label="Controlled Computer execution">
          <header><div><p class="section-kicker">CONTROLLED COMPUTER SKILL</p><h3>AI Execution Workspace</h3><p>AI-assisted execution with human approval and verification.</p></div><span class="computer-runtime-status">{{ selectedAIMission.worker_runtime?.computer_execution?.status || 'READY' }}</span></header>
          <section class="computer-runtime-goal"><div><span>CURRENT MISSION</span><b>{{ selectedAIMission.worker_runtime?.computer_execution?.task || 'Prepare a controlled task for this mission.' }}</b><small>{{ selectedAIMission.worker_runtime?.computer_execution?.next_action || 'Describe a bounded outcome for AI to prepare.' }}</small></div><div><span>EXPECTED OUTCOME</span><b>{{ selectedAIMission.worker_runtime?.computer_execution?.asset_status || 'A reviewable result, only when a controlled task completes.' }}</b><small>Important actions always require human confirmation.</small></div></section>
          <ol v-if="selectedAIMission.worker_runtime?.computer_execution?.stages?.length" class="computer-runtime-journey"><li v-for="stage in selectedAIMission.worker_runtime.computer_execution.stages" :key="stage.id" :class="stage.status.toLowerCase()"><span>{{ stage.status === 'COMPLETED' ? '✓' : stage.status === 'REQUIRED' ? '!' : stage.status === 'NEEDS_REVIEW' ? '•' : '○' }}</span><div><b>{{ stage.title }}</b><small>{{ stage.description }}</small></div></li></ol>
          <section v-if="selectedAIMission.worker_runtime?.computer_plan?.steps?.length" class="computer-runtime-plan"><span>AI PLAN</span><div v-for="step in selectedAIMission.worker_runtime.computer_plan.steps" :key="step.order"><b>{{ step.order }} · {{ step.skill }}</b><small>{{ step.purpose }}</small><em>{{ step.approval_required ? 'Human approval required' : 'Read-only or evidence-gated' }}</em></div></section>
          <section v-if="selectedAIMission.worker_runtime?.computer_execution?.verification" class="computer-runtime-verification"><span>VERIFICATION</span><b>{{ selectedAIMission.worker_runtime.computer_execution.verification.status }}</b><p>{{ selectedAIMission.worker_runtime.computer_execution.verification.summary }}</p><small v-if="selectedAIMission.worker_runtime.computer_execution.recovery">{{ selectedAIMission.worker_runtime.computer_execution.recovery.summary }}</small></section>
          <div class="computer-runtime-create"><input v-model="computerMissionTask" placeholder="Describe a controlled outcome for AI to prepare" /><button class="outline-button" type="button" :disabled="computerMissionLoading" @click="createComputerMission">Prepare task</button></div>
          <footer v-if="(selectedAIMission.computer_missions || []).length" class="computer-runtime-actions"><template v-for="item in selectedAIMission.computer_missions" :key="item.id"><button v-if="item.status === 'WAITING_APPROVAL'" class="primary-card-action" type="button" :disabled="computerMissionLoading" @click="decideComputerMission(item, 'APPROVED')">Confirm change</button><button v-if="item.status === 'WAITING_APPROVAL'" class="outline-button" type="button" :disabled="computerMissionLoading" @click="decideComputerMission(item, 'NEEDS_REVISION')">Request revision</button><button v-if="item.status === 'WAITING_APPROVAL'" class="text-button" type="button" :disabled="computerMissionLoading" @click="decideComputerMission(item, 'REJECTED')">Discard</button><button v-if="item.status === 'APPROVED' && item.execution_allowed" class="primary-card-action" type="button" :disabled="computerMissionLoading" @click="executeComputerMission(item)">Run approved action</button></template></footer>
        </section>
        <section v-if="selectedAIMission" class="artifact-studio">
          <header><div><p class="section-kicker">ARTIFACT AGENT</p><h3>Generate only the deliverable you need.</h3><p>每份产物都从当前 Mission 的真实 Evidence 与客户资料引用生成，且必须经过人工审核。</p></div><small v-if="artifactAnalytics">{{ artifactAnalytics.total_artifacts }} artifacts · {{ artifactAnalytics.average_evidence_coverage }}% evidence coverage</small></header>
          <p v-if="artifactError" class="error-alert"><span>!</span>{{ artifactError }}</p>
          <div class="artifact-action-row"><button v-for="item in [{type:'RESEARCH_BRIEF',label:'Research Brief'},{type:'SOLUTION_DOCUMENT',label:'Solution Document'},{type:'PRESENTATION',label:'Presentation'},{type:'DATA_REPORT',label:'Data Report'},{type:'DELIVERY_PACKAGE',label:'Delivery Package'}]" :key="item.type" class="outline-button" type="button" :disabled="artifactLoading" @click="generateMissionArtifact(item.type)">{{ item.label }}</button></div>
          <div v-if="missionArtifacts.length" class="artifact-grid"><button v-for="item in missionArtifacts" :key="item.id" type="button" class="artifact-card" :class="{ active: selectedArtifact?.id === item.id }" @click="openArtifact(item.id)"><span>{{ item.artifact_type }}</span><b>{{ item.title }}</b><small>v{{ item.version }} · {{ item.status }} · {{ item.evidence_count }} Evidence</small></button></div>
          <div v-else class="artifact-empty-state"><b>No artifact yet</b><p>选择一个交付物类型后生成可审核草稿；系统不会批量或自动生成。</p></div>
          <article v-if="selectedArtifact" class="artifact-review-surface"><header><div><span>{{ selectedArtifact.artifact_type }} · v{{ selectedArtifact.version }}</span><h4>{{ selectedArtifact.title }}</h4><p>{{ selectedArtifact.content_summary }}</p></div><small>{{ selectedArtifact.status }}</small></header><section><b>Evidence sources</b><p v-if="!selectedArtifact.evidence?.length">暂无可验证资料。草稿仅用于确认资料缺口，不包含科研结论。</p><div v-for="evidence in selectedArtifact.evidence || []" :key="evidence.evidence_type + '-' + (evidence.chunk_id || evidence.source)"><span>{{ evidence.evidence_type }}</span><small>{{ evidence.source }} · {{ evidence.section || 'Source reference' }}<template v-if="evidence.paper_id"> · {{ evidence.paper_id }} / {{ evidence.chunk_id }}</template></small></div></section><footer><template v-if="selectedArtifact.status === 'NEEDS_REVIEW'"><button class="primary-card-action" type="button" :disabled="artifactLoading" @click="reviewArtifact('APPROVED')">Approve delivery</button><button class="outline-button" type="button" :disabled="artifactLoading" @click="reviewArtifact('REVISION_REQUESTED')">Request revision</button><button class="text-button" type="button" :disabled="artifactLoading" @click="reviewArtifact('REJECTED')">Reject</button></template><button v-else-if="selectedArtifact.status === 'REVISION_REQUESTED'" class="primary-card-action" type="button" :disabled="artifactLoading" @click="reviseArtifact">Generate revised draft</button><button v-else-if="selectedArtifact.status === 'APPROVED'" class="primary-card-action" type="button" @click="downloadArtifact">Download approved artifact</button><small v-else>等待人工审核后才能作为正式交付下载。</small></footer></article>
        </section>
        <section class="mission-list"><button v-for="item in aiMissions" :key="item.id" type="button" :class="{ active: selectedAIMission?.id === item.id }" @click="loadAIMissionDetail(item.id)"><span>{{ item.type }}</span><b>{{ item.title }}</b><small>{{ item.status }} · {{ item.progress }}% · {{ item.current_step }}</small></button><p v-if="!aiMissions.length">No AI mission yet. Create a mission to begin a reviewable lifecycle.</p></section>
      </section>

      <section v-if="activeWorkspaceView === 'mission-center' && selectedAIMission?.collaboration" class="mission-tool-trace collaboration-panel" aria-label="Agent Collaboration"><p class="section-kicker">AGENT COLLABORATION</p><h3>Structured collaboration, not hidden reasoning.</h3><p v-if="!selectedAIMission.collaboration.messages?.length" class="quiet-note">尚无 Agent Message。消息仅在实际协作请求、结果、反馈或风险告警发生时记录。</p><article v-for="item in selectedAIMission.collaboration.messages || []" :key="item.id"><b>{{ item.sender_agent }} → {{ item.receiver_agent }}</b><small>Round {{ item.collaboration_round }} · {{ item.message_type }} · {{ item.status }}</small><p>{{ item.payload_summary }}</p></article><div v-for="item in selectedAIMission.collaboration.conflicts || []" :key="item.id" class="collaboration-conflict"><b>Human review required</b><small>{{ item.participants?.join(' ↔ ') }}</small><p>{{ item.summary }}</p></div></section>

      <section v-if="activeWorkspaceView === 'mission-center' && selectedAIMission?.worker_runtime" class="mission-tool-trace" aria-label="AI Worker Execution"><p class="section-kicker">AI WORKER EXECUTION</p><h3>Task → Skills → Progress → Review</h3><p v-if="selectedAIMission.worker_runtime.waiting_action" class="quiet-note">{{ selectedAIMission.worker_runtime.waiting_action }}</p><article v-for="item in selectedAIMission.worker_runtime.timeline || []" :key="item.id"><b>{{ item.skill }}</b><small>{{ item.action_type }} · {{ item.status }} · {{ item.created_at }}</small><p>{{ item.result_summary }}</p></article><p v-if="!(selectedAIMission.worker_runtime.timeline || []).length" class="quiet-note">AI Worker is ready. Execution records appear only after a real controlled Skill runs.</p></section>

      <section v-if="activeWorkspaceView === 'mission-center' && selectedAIMission?.tools_used?.length" class="mission-tool-trace" aria-label="Mission Tool Trace"><p class="section-kicker">TOOLS USED</p><h3>Read-only enterprise operations</h3><article v-for="item in selectedAIMission.tools_used" :key="item.connector_name + item.operation + item.duration_ms"><b>{{ item.connector_name }}</b><small>{{ item.operation }} · {{ item.status }} · {{ item.duration_ms }}ms</small><p>{{ item.result_summary }}</p></article></section>

      <section v-if="activeWorkspaceView === 'governance'" class="connector-center" aria-label="Governance Center"><header class="dashboard-heading"><div><p class="section-kicker">ADMIN CONSOLE</p><h2>Governance and oversight</h2><p>Workspace RBAC、Audit 与 Policy 均基于真实持久化记录；不展示凭据、Prompt 或模型内部状态。</p></div><button class="outline-button" type="button" @click="loadGovernance">Refresh</button></header><nav class="admin-console-sections" aria-label="Admin Console sections"><button type="button" class="active">Governance & Audit</button><button type="button" @click="openWorkspaceView('system')">Runtime & Diagnostics</button><button type="button" @click="openWorkspaceView('benchmarks')">Evaluation</button></nav><div class="connector-metrics"><article><b>{{ governance.organizations.length }}</b><small>Organizations</small></article><article><b>{{ governance.workspaces.length }}</b><small>Workspaces</small></article><article><b>{{ governance.logs.length }}</b><small>Audit events</small></article><article><b>RBAC</b><small>API enforced</small></article></div><div v-if="governance.logs.length" class="connector-grid"><article v-for="item in governance.logs" :key="item.created_at + item.action"><header><span>{{ item.action }}</span><b>{{ item.resource_type }}</b></header><p>{{ item.summary }}</p><small>{{ item.user_id }} · {{ item.workspace_id || 'Organization' }}</small></article></div><div v-else class="product-empty-state"><b>No governed activity yet</b><p>创建 Organization、设置角色或更新 Policy 后，系统会保存不含 Prompt、CoT 和 Secret 的审计摘要。</p></div></section>
      <section v-if="activeWorkspaceView === 'benchmarks'" class="connector-center" aria-label="Agent Benchmark Center"><header class="dashboard-heading"><div><p class="section-kicker">AGENT EVALUATION</p><h2>Agent Benchmark Center</h2><p>评分只来自真实 Benchmark Mission 的 Trace、Evidence、Artifact 与 Human Review 状态；未运行时保持 0。</p></div><button class="outline-button" type="button" @click="loadBenchmarks">Refresh</button></header><div v-if="benchmarkDashboard" class="connector-metrics"><article><b>{{ benchmarkDashboard.benchmarks }}</b><small>Benchmarks</small></article><article><b>{{ benchmarkDashboard.runs }}</b><small>Runs</small></article><article><b>{{ benchmarkDashboard.average_score }}</b><small>Average score</small></article><article><b>{{ benchmarkDashboard.success_rate }}%</b><small>Success rate</small></article></div><div v-if="benchmarkDashboard" class="connector-grid"><article v-for="(score, capability) in benchmarkDashboard.capabilities" :key="capability"><header><span>OBSERVED</span><b>{{ capability }}</b></header><p>{{ score }} / 100</p><small>Derived from saved benchmark records only.</small></article></div><div v-if="benchmarkTasks.length" class="connector-grid"><article v-for="task in benchmarkTasks" :key="task.id"><header><span>{{ task.category }}</span><b>{{ task.difficulty }}</b></header><h3>{{ task.name }}</h3><p>{{ task.description }}</p><small>{{ task.expected_agents.length }} expected agents · {{ task.expected_tools.length }} expected tools</small></article></div><div v-else class="product-empty-state"><b>No benchmark task yet</b><p>创建并显式运行受控 Benchmark 后，这里才会显示实际评分，系统不会生成假分数。</p></div></section>
      <section v-if="activeWorkspaceView === 'scenario-center'" class="connector-center" aria-label="Enterprise Scenario Center"><header class="dashboard-heading"><div><p class="section-kicker">ENTERPRISE SCENARIO DEMO</p><h2>Scenario Center</h2><p>通过同一条 Mission Runtime 演示需求理解、资料检索、风险提示、待审核 Artifact 与 Benchmark 观察；所有场景均为 DEMO_ONLY。</p></div><button class="outline-button" type="button" @click="loadScenarios">Refresh</button></header><div v-if="enterpriseScenarios.length" class="connector-grid"><article v-for="item in enterpriseScenarios" :key="item.id"><header><span>DEMO_ONLY</span><b>{{ item.industry }}</b></header><h3>{{ item.name }}</h3><p>{{ item.description }}</p><small>AI Team · {{ item.expected_agents.join(' · ') }}</small><footer><button class="primary-card-action" :disabled="scenarioLoading" type="button" @click="runScenario(item.id)">{{ scenarioLoading ? 'Running controlled mission…' : 'Run scenario' }}</button></footer></article></div><div v-else class="product-empty-state"><b>No scenario available</b><p>没有已声明的 Demo 场景；系统不会以虚构客户数据填充该页面。</p></div><section v-if="scenarioRunResult" class="mission-tool-trace"><p class="section-kicker">SCENARIO RUN</p><h3>{{ scenarioRunResult.scenario.name }} · {{ scenarioRunResult.status }}</h3><p>{{ scenarioRunResult.boundary }}</p><article v-for="item in scenarioRunResult.timeline" :key="item.created_at + item.action"><b>{{ item.stage }}</b><small>{{ item.status }} · Evidence {{ item.evidence_count }}</small><p>{{ item.result_summary }}</p></article><article v-if="scenarioRunResult.artifact"><b>Artifact</b><small>{{ scenarioRunResult.artifact.status }} · Human Review required</small><p>{{ scenarioRunResult.artifact.content_summary || 'Reviewable draft generated.' }}</p></article><article v-if="scenarioRunResult.benchmark"><b>Observed Benchmark</b><small>{{ scenarioRunResult.benchmark.score }} · same Mission</small><p>{{ scenarioRunResult.benchmark.trace_summary }}</p></article></section></section>
      <section v-if="activeWorkspaceView === 'ai-workspace'" class="connector-center" aria-label="AI Worker Workspace"><header class="dashboard-heading"><div><p class="section-kicker">WORKSPACE CONTEXT</p><h2>Enterprise AI Workspace</h2><p>Current work is grounded in your authorized Workspace, traceable Evidence, approved knowledge, and reviewable memory.</p></div><button class="outline-button" type="button" @click="loadUnifiedWorkspaceContext">Refresh context</button></header><section class="workspace-context-panel"><article><span>Workspace</span><b>{{ workspaceContext?.workspace?.id ? currentWorkspace?.name : 'Loading authorized context' }}</b><small>{{ currentWorkspace?.member_count || 0 }} members · {{ currentRole || 'Authorized role' }}</small></article><article><span>Current mission</span><b>{{ workspaceExperience?.missions?.[0]?.title || 'No active mission' }}</b><small>{{ workspaceExperience?.missions?.[0]?.current_step || 'Create a Mission to begin a controlled workflow.' }}</small></article><article><span>Research memory</span><b>{{ researchMemory.length }} traceable record{{ researchMemory.length === 1 ? '' : 's' }}</b><small>Preferences, approved knowledge and mission history stay Workspace-scoped.</small></article></section><p v-if="workspaceContextError" class="quiet-note">Context details are temporarily unavailable. Existing Workspace data remains unchanged.</p><div v-if="workspaceExperience" class="connector-metrics"><article><b>{{ workspaceExperience.active_missions }}</b><small>Active missions</small></article><article><b>{{ workspaceExperience.reviews.pending }}</b><small>Pending review</small></article><article><b>{{ workspaceExperience.artifacts.length }}</b><small>Recent artifacts</small></article><article><b>{{ aiWorkerSkills.length }}</b><small>Controlled skills</small></article></div><div v-if="workspaceExperience" class="connector-grid"><article v-for="item in workspaceExperience.missions" :key="item.id"><header><span>{{ item.status }}</span><b>{{ item.progress }}%</b></header><h3>{{ item.title }}</h3><p>{{ item.current_step }}</p><small>Evidence · {{ item.evidence_refs.length }} · {{ item.created_at }}</small><button class="text-button" type="button" @click="openWorkspaceView('mission-center'); loadAIMissionDetail(item.id)">Open Mission →</button></article></div><div v-if="workspaceExperience && !workspaceExperience.missions.length" class="product-empty-state"><b>No mission yet</b><p>Create a Mission to connect AI Worker Skills, traceable Evidence, Research Memory and Human Review in one Workspace.</p></div><section v-if="researchMemory.length" class="research-memory-surface"><header><div><p class="section-kicker">RESEARCH MEMORY</p><h3>Reusable Workspace context</h3><p>Compact records show their source, lifecycle and use. Sensitive source material and internal reasoning are never stored here.</p></div><small>{{ researchMemory.length }} active record{{ researchMemory.length === 1 ? '' : 's' }}</small></header><p v-if="researchMemoryActionError" class="quiet-note">{{ researchMemoryActionError }}</p><article v-for="item in researchMemory.slice(0, 4)" :key="item.id"><div><b>{{ item.title }}</b><small>{{ item.memory_type }} · {{ item.source_type }} · {{ item.importance_score }}/100 importance · {{ item.lifecycle_state.replaceAll('_', ' ') }}</small><p>{{ item.summary }}</p><em>{{ item.references?.length || 0 }} linked reference{{ item.references?.length === 1 ? '' : 's' }} · used {{ item.use_count || 0 }} time{{ item.use_count === 1 ? '' : 's' }}</em></div><footer><button class="text-button" type="button" @click="explainResearchMemory(item.id)">Why available</button><button v-if="['OWNER','ADMIN','MANAGER','REVIEWER'].includes(currentRole) && item.lifecycle_state !== 'VERIFIED'" class="text-button" type="button" @click="manageResearchMemory(item.id, 'validate')">Verify</button><button class="text-button" type="button" @click="manageResearchMemory(item.id, 'archive')">Archive</button><button class="text-button danger-action" type="button" @click="manageResearchMemory(item.id, 'delete')">Remove</button></footer></article><aside v-if="selectedResearchMemory" class="research-memory-explanation"><b>{{ selectedResearchMemory.title }}</b><p>{{ selectedResearchMemory.explanation }}</p><small>{{ selectedResearchMemory.references?.length || 0 }} traceable reference{{ selectedResearchMemory.references?.length === 1 ? '' : 's' }} · {{ selectedResearchMemory.lifecycle_state.replaceAll('_', ' ') }}</small></aside></section><section v-if="workspaceExperience?.artifacts.length" class="mission-tool-trace"><p class="section-kicker">RECENT ARTIFACTS</p><article v-for="item in workspaceExperience.artifacts" :key="item.id"><b>{{ item.title }}</b><small>{{ item.artifact_type }} · v{{ item.version }} · {{ item.status }}</small><p>Evidence {{ item.evidence_count }} · {{ item.created_at }}</p></article></section></section>
      <section v-if="activeWorkspaceView === 'memory-center'" class="connector-center" aria-label="Enterprise Memory Center"><header class="dashboard-heading"><div><p class="section-kicker">ENTERPRISE KNOWLEDGE MEMORY</p><h2>Enterprise Memory Center</h2><p>只有经人工审批的决策才会成为可复用的企业知识资产；客户文件与 Demo 数据不会自动进入 Experience Library。</p></div><button class="outline-button" type="button" @click="loadKnowledgeMemory">Refresh</button></header><div v-if="knowledgeMemory.dashboard" class="connector-metrics"><article><b>{{ knowledgeMemory.dashboard.approved_knowledge }}</b><small>Approved knowledge</small></article><article><b>{{ knowledgeMemory.dashboard.decision_count }}</b><small>Decision records</small></article><article><b>{{ knowledgeMemory.dashboard.average_confidence }}</b><small>Avg confidence</small></article><article><b>{{ knowledgeMemory.dashboard.experience_reuse_count }}</b><small>Experience reuse</small></article></div><div class="connector-grid"><article v-for="item in knowledgeMemory.assets" :key="item.id"><header><span>{{ item.status }}</span><b>{{ item.confidence }}/100</b></header><h3>{{ item.title }}</h3><p>{{ item.summary }}</p><small>{{ item.asset_type }} · {{ item.source_type }}</small></article></div><section v-if="knowledgeMemory.decisions.length" class="mission-tool-trace"><p class="section-kicker">DECISION RECORDS</p><article v-for="item in knowledgeMemory.decisions" :key="item.id"><b>{{ item.title }}</b><small>{{ item.review_status }} · Evidence {{ item.evidence_refs.length }}</small><p>{{ item.decision_summary }}</p></article></section><div v-if="!knowledgeMemory.assets.length && !knowledgeMemory.decisions.length" class="product-empty-state"><b>No approved enterprise memory yet</b><p>完成 Mission 后会生成待审核 Decision Draft；只有 Reviewer 审批后才可进入 Experience Library。</p></div></section>
      <section v-if="['showcase','architecture','capabilities','business-dashboard','release-center'].includes(activeWorkspaceView)" class="connector-center" aria-label="Product Showcase"><header class="dashboard-heading"><div><p class="section-kicker">{{ activeWorkspaceView === 'showcase' ? 'DEMO_ONLY · ENTERPRISE DEMO CENTER' : 'RESEARCHOS PRODUCT SHOWCASE' }}</p><h2>{{ activeWorkspaceView === 'architecture' ? 'Enterprise Architecture' : activeWorkspaceView === 'capabilities' ? 'AI Capability Center' : activeWorkspaceView === 'business-dashboard' ? 'Business Overview' : activeWorkspaceView === 'release-center' ? 'Release Center' : 'Enterprise AI Agent Workspace' }}</h2><p>{{ productShowcase.overview?.subtitle || 'From Business Problem To AI-powered Solution' }}</p></div><button class="outline-button" type="button" @click="loadProductShowcase">Refresh</button></header><div v-if="activeWorkspaceView === 'showcase' && productShowcase.workflow" class="connector-grid"><article v-for="(step,index) in productShowcase.workflow.steps" :key="step.title"><header><span>STEP {{ index + 1 }}</span><b>{{ productShowcase.workflow.classification }}</b></header><h3>{{ step.title }}</h3><p>{{ step.summary }}</p></article></div><div v-if="activeWorkspaceView === 'architecture'" class="mission-tool-trace"><h3>User → AI Workspace → Copilot Layer → Mission Engine → Planner → Agent Runtime → Agent Team</h3><p>RAG Knowledge · Connector · Computer Agent · Artifact · Human Review · Governance · Knowledge Memory</p></div><div v-if="activeWorkspaceView === 'capabilities' && productShowcase.capabilities" class="connector-grid"><article v-for="item in productShowcase.capabilities.groups" :key="item.name"><h3>{{ item.name }}</h3><p>{{ item.items.join(' · ') }}</p></article></div><div v-if="activeWorkspaceView === 'business-dashboard' && productShowcase.business" class="connector-metrics"><article v-for="(value,key) in productShowcase.business" v-if="!['data_state','boundary'].includes(key)" :key="key"><b>{{ value }}</b><small>{{ key }}</small></article></div><div v-if="activeWorkspaceView === 'release-center' && productShowcase.releases" class="connector-grid"><article v-for="item in productShowcase.releases.releases" :key="item[0]"><b>{{ item[0] }}</b><p>{{ item[1] }}</p></article></div></section>

      <section v-if="activeWorkspaceView === 'connector-center'" class="connector-center" aria-label="Enterprise Connector Center">
        <header class="dashboard-heading"><div><p class="section-kicker">ENTERPRISE TOOL INTEGRATION</p><h2>Connector Center</h2><p>Connector 默认只读、全程留痕。P31 仅实际启用 SQLite；PostgreSQL/MySQL 不接收凭证且保持禁用。</p></div><button class="outline-button" type="button" :disabled="connectorLoading" @click="loadConnectorCenter">Refresh</button></header>
        <p v-if="connectorError" class="error-alert"><span>!</span>{{ connectorError }}</p>
        <div v-if="connectorAnalytics" class="connector-metrics"><article><b>{{ connectorAnalytics.connectors }}</b><small>Connectors</small></article><article><b>{{ connectorAnalytics.tool_usage_count }}</b><small>Read-only calls</small></article><article><b>{{ connectorAnalytics.connector_success_rate }}%</b><small>Success rate</small></article><article><b>{{ connectorAnalytics.average_duration_ms }}ms</b><small>Average duration</small></article></div>
        <section class="connector-register"><div><p class="section-kicker">REGISTER SQLITE</p><h3>Attach a read-only data source</h3><p>仅接受已有 .db/.sqlite/.sqlite3 路径；不会保存密码、Token 或数据库写权限。</p></div><input v-model="connectorForm.name" placeholder="Connector name" /><input v-model="connectorForm.sqlite_path" placeholder="Existing SQLite file path" /><button class="primary-card-action" type="button" :disabled="connectorLoading" @click="registerSqliteConnector">Register read-only</button></section>
        <div v-if="connectors.length" class="connector-grid"><article v-for="connector in connectors" :key="connector.id"><header><span :class="connector.status">{{ connector.status }}</span><b>{{ connector.name }}</b></header><p>{{ connector.type }} · {{ connector.permission }}</p><small v-for="source in connector.data_sources || []" :key="source.id">{{ source.name }} · {{ source.type }}</small></article></div><div v-else class="product-empty-state"><b>No connector registered</b><p>注册受控的只读 SQLite 数据源后，Agent 才能在 Mission 中引用其真实数据。</p></div>
      </section>

      <section v-if="activeWorkspaceView === 'artifact-center'" class="product-experience-center" aria-label="AI Delivery Room"><header class="dashboard-heading"><div><p class="section-kicker">AI DELIVERY ROOM</p><h2>Outputs stay linked to review.</h2><p>Research drafts and Computer artifacts remain versioned, evidence-aware and ready for a human decision.</p></div><button class="outline-button" type="button" @click="openWorkspaceView('dashboard')">Back to Command Center</button></header><div v-if="artifactGallery.length" class="product-artifact-grid"><article v-for="item in artifactGallery" :key="item.category + item.id"><span>{{ item.category }}</span><h3>{{ item.title }}</h3><p>{{ item.type }} · {{ item.status }}</p><small>Reference · {{ item.reference }}</small><button class="text-button" type="button" @click="item.category === 'Computer' ? openWorkspaceView('computer') : openWorkspaceView('outcome-center')">Open & review →</button></article></div><div v-else class="product-empty-state"><b>Your first delivery starts with a mission</b><p>Run a controlled research or Computer workflow to create an output ready for review.</p><button class="primary-card-action" type="button" @click="openWorkspaceView('dashboard')">Start a mission</button></div></section>

      <section v-if="activeWorkspaceView === 'demo-center'" class="product-experience-center" aria-label="Demo Scenario Center"><header class="dashboard-heading"><div><p class="section-kicker">DEMO SCENARIO CENTER</p><h2>Three bounded ways to experience ResearchOS.</h2><p>所有入口均标记为 Demo；不会生成假 Evidence、研究结论或未经批准的源码修改。</p></div></header><div class="product-demo-grid"><article v-for="item in productDemos" :key="item.id"><span>DEMO</span><h3>{{ item.title }}</h3><ol><li v-for="step in item.steps" :key="step">{{ step }}</li></ol><p>{{ item.boundary }}</p><button class="primary-card-action" type="button" @click="startProductDemo(item)">Open demo</button></article></div></section>

      <aside v-if="onboardingOpen" class="product-onboarding-layer" aria-label="ResearchOS welcome"><div><p class="section-kicker">WELCOME TO RESEARCHOS</p><h2>AI Research Operating System</h2><p>From Research Question to Evidence-backed Decision</p><div class="onboarding-choice-grid"><button type="button" @click="completeOnboarding('research'); beginResearchFromHome('Explore a research goal with evidence-backed workflow.')"><b>Explore Research</b><small>输入并探索研究目标</small></button><button type="button" @click="completeOnboarding('workflow'); openWorkspaceView('workflow-studio')"><b>Build Research Workflow</b><small>创建可审阅研究流程</small></button><button type="button" @click="completeOnboarding('computer'); openWorkspaceView('computer')"><b>Use Computer Skill</b><small>分析项目和受控改动</small></button></div><button class="text-button" type="button" @click="completeOnboarding('welcome')">Explore later</button></div></aside>

       <button class="research-assistant-launcher" type="button" @click="assistantPanelOpen = !assistantPanelOpen" :aria-expanded="assistantPanelOpen"><svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M12 3.5 14 10l6.5 2-6.5 2-2 6.5-2-6.5-6.5-2 6.5-2 2-6.5Z" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/></svg>Research Assistant</button>
      <aside v-if="assistantPanelOpen" class="research-assistant-panel" aria-label="Research Assistant"><header><div><span>Research Copilot</span><h3>从研究问题开始</h3></div><button type="button" @click="assistantPanelOpen = false" aria-label="关闭 Research Assistant">×</button></header><p>我可以帮你创建研究任务、推荐研究策略，或恢复已有 Workspace。</p><div class="copilot-suggestions"><button type="button" @click="beginResearchFromHome('比较当前已索引资料中的研究方法与适用条件。')">创建研究任务</button><button type="button" @click="beginResearchFromHome('根据当前 Evidence 推荐合适的研究策略。')">推荐研究策略</button><button type="button" @click="openWorkspaceView('research-workspace'); assistantPanelOpen = false">打开 Workspace</button></div><textarea v-model="assistantDraft" rows="4" placeholder="例如：比较当前资料中 RAG 方法的适用条件"></textarea><button type="button" class="primary-card-action" @click="sendAssistantToResearch">进入 Research</button><small v-if="!readyPaperCount">当前知识库没有足够资料支持该研究，请先上传并完成索引。</small><small v-else>这是已有 Research Command 的任务入口，不会创建独立聊天记录或虚构结论。</small></aside>

      <section v-if="activeWorkspaceView === 'demo'" class="demo-stage ai-workspace-hero" aria-label="悟帆比赛现场演示模式">
        <div class="workspace-hero-copy">
          <p class="section-eyebrow">RESEARCHOS AI WORKSPACE · 悟帆比赛现场模式</p>
          <h1>让科研知识<br /><em>转化为创新决策。</em></h1>
          <p>连接高校科研能力与企业创新需求，帮助团队完成从研究方向发现到成果规划全过程。</p>
          <div class="hero-goal-input"><span>✦</span><input v-model="researchOsGoal" aria-label="科研目标" placeholder="请输入您的科研目标、企业需求或研究问题" /><button type="button" @click="startDemoMode">开始协作</button></div>
          <div class="hero-quick-actions"><button type="button" @click="applyFdeDeliveryDemo"><b>企业需求分析</b><small>生成产学研合作方案</small></button><button type="button" @click="selectAdvisorScenario('explore')"><b>研究方向探索</b><small>发现趋势与创新机会</small></button><button type="button" @click="openWorkspaceView('knowledge')"><b>实验室知识管理</b><small>沉淀团队科研资产</small></button></div>
        </div>
        <aside class="ai-task-space">
          <div class="ai-task-space-head"><div><span>现场案例</span><h2>低碳建筑材料企业合作</h2></div><i>AI 协作中</i></div>
          <p class="task-demand">企业需求：寻找低碳建筑材料研发方案，兼顾工程适用性与科研成果。</p>
          <div class="agent-orbit"><span>Research<br />Master</span><i>Knowledge<br />Agent</i><i>Innovation<br />Agent</i><i>Project<br />Agent</i></div>
          <section class="ai-activity-stream" aria-label="AI Activity Stream"><div><span>AI Activity</span><b>{{ researchOsTaskLoading ? 'AI 团队正在协作' : researchOsTaskResult ? '本次协作已完成' : '等待任务启动' }}</b></div><article v-for="item in aiActivityStream" :key="item.agent" :class="item.status"><i></i><p><strong>{{ item.agent }}</strong>{{ item.action }}</p><em>{{ item.label }}</em></article></section>
          <div class="demo-report-preview"><div><span>输出目标</span><b>FDE 解决方案报告</b></div><button type="button" @click="openWorkspaceView('fde-report')">查看报告 →</button></div>
        </aside>
        <div class="demo-flow-board workspace-flow-board"><article v-for="(item, index) in demoSteps" :key="item.id" class="demo-flow-step"><span class="demo-step-number">{{ index + 1 }}</span><div><h3>{{ item.title }}</h3><p>{{ item.detail }}</p></div><button class="text-button" type="button" @click="openDemoStep(item)">打开</button></article></div>
        <p class="demo-boundary">一键演示仅预填真实任务与项目资料；能力匹配、技术路线、创新机会和报告结论仍需通过已有 Agent 基于上传资料实际生成。</p>
      </section>

      <section v-if="activeWorkspaceView === 'dashboard-detail'" class="researchos-dashboard" aria-label="ResearchOS 科研驾驶舱">
        <div class="dashboard-heading"><div><p class="section-kicker">RESEARCH COMMAND CENTER</p><h2>科研驾驶舱</h2><p>将团队已上传的科研资料转化为可复核的知识、洞察和行动建议。</p></div><span>某高校建筑材料实验室 · 示例工作空间</span></div>
        <section class="advisor-entry"><div><p class="section-kicker">WHO IS USING RESEARCHOS</p><h3>选择你的角色视角</h3><p>{{ advisorRoles.find((item) => item.id === advisorAudience)?.description }}</p></div><div class="advisor-role-options"><button v-for="item in advisorRoles" :key="item.id" type="button" :class="{ active: advisorAudience === item.id }" @click="advisorAudience = item.id">{{ item.name }}</button></div></section>
        <section class="advisor-scenarios"><article><span>01</span><h3>企业需求分析</h3><p>从企业需求到实验室能力匹配、技术建议与成果路径。</p><button type="button" @click="selectAdvisorScenario('enterprise')">进入 FDE 交付</button></article><article><span>02</span><h3>研究方向探索</h3><p>从团队资料中归纳趋势、创新机会与验证任务。</p><button type="button" @click="selectAdvisorScenario('explore')">开始探索</button></article><article><span>03</span><h3>实验室知识管理</h3><p>统一管理论文、专利、实验报告和项目资料。</p><button type="button" @click="selectAdvisorScenario('knowledge')">管理资料</button></article></section>
        <div class="dashboard-stat-grid"><article><span>科研论文</span><strong>{{ researchOsOverview?.paper_count ?? libraryPapers.length }}</strong><small>当前已纳入知识空间</small></article><article><span>知识片段</span><strong>{{ researchOsOverview?.knowledge_chunk_count ?? knowledgeChunkTotal }}</strong><small>用于检索与证据引用</small></article><article><span>索引就绪</span><strong>{{ researchOsOverview?.ready_paper_count ?? readyPaperCount }}</strong><small>可参与多论文问答</small></article><article><span>研究报告</span><strong>{{ researchOverview?.analysis_count ?? 0 }}</strong><small>历史分析成果</small></article></div>
        <div class="researchos-dashboard-grid"><section class="dashboard-card"><p class="section-kicker">AI RESEARCH INSIGHT</p><h3>从资料到研究决策</h3><ol class="researchos-flow"><li>上传论文与科研资料</li><li>Research Master 理解目标并编排任务</li><li>专项 Agent 基于知识库检索证据</li><li>生成趋势、创新机会与成果规划建议</li></ol><button class="outline-button" type="button" @click="openWorkspaceView('knowledge')">管理科研知识库</button></section><section class="dashboard-card accent-card"><p class="section-kicker">FDE DELIVERY CASE</p><h3>低碳建筑材料企业需求</h3><p>企业需求 → 实验室匹配 → 技术路线 → 创新机会 → 项目规划 → 成果预测。</p><button class="primary-card-action" type="button" @click="applyFdeDeliveryDemo">启动完整 FDE 演示</button><small>实际结果必须由已上传资料和 Agent 调用生成。</small></section></div>
        <div class="researchos-dashboard-grid lifecycle-preview"><section class="dashboard-card"><p class="section-kicker">PROJECT LIFECYCLE</p><h3>科研项目生命周期</h3><div class="lifecycle-strip"><span>项目创建</span><i>→</i><span>研究目标</span><i>→</i><span>技术路线</span><i>→</i><span>论文 / 专利规划</span><i>→</i><span>成果管理</span></div><button class="outline-button" type="button" @click="openWorkspaceView('projects')">进入科研项目中心</button></section><section class="dashboard-card"><p class="section-kicker">RESEARCH BI</p><h3>科研资产与技术路线</h3><p>查看当前资料构成、知识片段、项目数与基于资料的趋势分析入口。</p><button class="outline-button" type="button" @click="openWorkspaceView('bi')">打开科研 BI 驾驶舱</button></section></div>
        <section class="lab-profile-card"><div><p class="section-kicker">LAB PROFILE</p><h3>实验室科研能力画像</h3><p>由 Knowledge Agent 根据已上传资料归纳研究方向、核心能力、成果线索与合作方向。</p></div><button class="outline-button" type="button" :disabled="labProfileLoading" @click="generateLabProfile">{{ labProfileLoading ? '生成中…' : '生成能力画像' }}</button><div v-if="labProfile" class="lab-profile-grid"><article><h4>研究方向</h4><ul><li v-for="item in labProfile.research_directions" :key="item">{{ item }}</li></ul></article><article><h4>核心能力</h4><ul><li v-for="item in labProfile.core_capabilities" :key="item">{{ item }}</li></ul></article><article><h4>成果线索</h4><ul><li v-for="item in labProfile.research_outputs" :key="item">{{ item }}</li></ul></article><article><h4>合作方向</h4><ul><li v-for="item in labProfile.collaboration_directions" :key="item">{{ item }}</li></ul></article></div><small v-if="labProfile">{{ labProfile.boundary_note }}</small></section>
        <p v-if="researchOsError" class="error-alert"><span>!</span>{{ researchOsError }}</p>
      </section>

      <section v-if="activeWorkspaceView === 'research-workspace'" class="research-intelligence-workspace" aria-label="Research Workspace">
        <header class="research-intelligence-heading"><div><p class="section-kicker">CONTINUOUS RESEARCH</p><h2>Research Workspace</h2><p>每个 Workspace 保留研究策略、Evidence、冲突提示、人工审核和交付草案，让研究可以持续推进。</p></div><div class="workspace-heading-actions"><button class="outline-button" type="button" @click="applyResearchWorkspaceDemo">体验 RAG 优化 Demo</button><button class="outline-button" type="button" :disabled="workspaceIntelligenceLoading" @click="loadResearchWorkspaces">{{ workspaceIntelligenceLoading ? '同步中…' : '刷新工作空间' }}</button></div></header>
        <p v-if="workspaceIntelligenceError" class="error-alert"><span>!</span>{{ workspaceIntelligenceError }}</p>
        <div v-if="workspaceIntelligenceLoading && !researchWorkspaces.length" class="loading-state"><span class="spinner"></span><p>正在加载已保存的研究工作空间…</p></div>
        <div v-else-if="!researchWorkspaces.length" class="workspace-intelligence-empty"><b>✦</b><h3>还没有持续研究项目</h3><p>在 Research Command 中完成一次有 Evidence 的研究任务后，系统会自动创建并保存工作空间。</p><button class="primary-card-action" type="button" @click="openWorkspaceView('tasks')">前往 Research Command</button></div>
        <div v-else class="research-intelligence-layout">
          <aside class="research-workspace-list"><p>持续研究项目</p><button v-for="item in researchWorkspaces" :key="item.workspace_id" type="button" :class="{ active: selectedResearchWorkspace?.workspace_id === item.workspace_id }" @click="loadResearchWorkspaceDetails(item.workspace_id)"><span>{{ item.strategy_type || 'research' }}</span><strong>{{ item.title }}</strong><small>{{ item.evidence_count || 0 }} Evidence · {{ item.human_review_required ? '待人工审核' : item.status }}</small></button></aside>
          <main v-if="selectedResearchWorkspace" class="research-workspace-detail">
            <section class="workspace-goal-card"><span>{{ selectedResearchWorkspace.status }}</span><h3>{{ selectedResearchWorkspace.title }}</h3><p>{{ selectedResearchWorkspace.research_goal || '尚未记录研究目标。' }}</p><small>策略：{{ selectedResearchWorkspace.strategy_type || '未记录' }} · Evidence：{{ selectedResearchWorkspace.evidence_count || 0 }} 条</small></section>
            <section class="workspace-workflow-board"><header><div><p class="section-kicker">TEAM WORKFLOW</p><h3>研究进度</h3></div><span>{{ workspaceWorkflow?.current_state || 'created' }}</span></header><ol><li v-for="state in ['created','research_planning','evidence_collection','evidence_review','decision_pending','deliverable_draft','completed']" :key="state" :class="{ active: workspaceWorkflow?.history?.includes(state), current: workspaceWorkflow?.current_state === state }">{{ state.replaceAll('_', ' ') }}</li></ol><p>{{ workspaceWorkflow?.reason }}</p></section>
            <section class="workspace-collaboration-board"><header><div><p class="section-kicker">TEAM MEMBERS</p><h3>Research Team Workspace</h3></div><small>展示权限模型，不含账号系统</small></header><article v-for="member in workspaceMembers" :key="member.role_type"><span>{{ member.user_role }}</span><strong>{{ member.role_type }}</strong><p>{{ member.permissions?.join(' · ') }}</p></article></section>
            <section class="workspace-trace-card"><header><div><p class="section-kicker">RESEARCH TIMELINE</p><h3>AI 如何完成本次研究</h3></div><span>{{ selectedResearchWorkspace.human_review?.required ? 'Human Review required' : 'Ready for review' }}</span></header><ol><li v-for="(item, index) in selectedResearchWorkspace.tasks || []" :key="item.subtask_id"><b>{{ index + 1 }}</b><div><span>{{ item.status }}</span><strong>{{ item.title }}</strong><p>{{ item.purpose || item.expected_evidence || '基于当前资料执行。' }}</p></div><em>{{ item.evidence_count || 0 }} Evidence</em></li></ol></section>
            <section class="workspace-quality-card"><header><div><p class="section-kicker">RESEARCH SUPPORT QUALITY</p><h3>研究支持质量</h3></div><small>不是 Accuracy</small></header><div v-if="workspaceQuality" class="workspace-metric-grid"><article v-for="(value, key) in workspaceQuality.metrics" :key="key"><span>{{ key.replaceAll('_', ' ') }}</span><b>{{ value === true ? 'Required' : value === false ? 'Not required' : value }}</b></article></div><p>{{ workspaceQuality?.support_note }}</p></section>
            <section class="workspace-decision-card"><p class="section-kicker">RESEARCH DECISION · HUMAN IN THE LOOP</p><h3>待确认研究判断</h3><p>{{ workspaceDecisionCandidate?.statement || '正在准备 Evidence 依据。' }}</p><details><summary>查看 Evidence 依据（{{ workspaceDecisionCandidate?.evidence_refs?.length || 0 }}）</summary><ul><li v-for="ref in workspaceDecisionCandidate?.evidence_refs || []" :key="ref.evidence_id"><strong>{{ ref.source || '未命名资料' }}</strong><span>{{ ref.chapter || '正文' }} · {{ ref.score ?? '—' }}</span></li></ul></details><p class="workspace-next-action"><b>下一步：</b>{{ workspaceDecisionCandidate?.next_action }}</p><small>{{ workspaceDecisionCandidate?.boundary }}</small></section>
            <section class="workspace-review-board"><header><div><p class="section-kicker">REVIEW CENTER</p><h3>人工审核队列</h3></div><span>{{ workspaceReviews?.filter(item => item.status === 'pending').length || 0 }} pending</span></header><article v-for="item in workspaceReviews" :key="item.id"><div><b>{{ item.type }}</b><h4>{{ item.statement }}</h4><p>{{ item.evidence_refs?.length || 0 }} 条 Evidence · {{ item.status }}</p><small v-if="item.reviewer_note">{{ item.reviewer_role }}：{{ item.reviewer_note }}</small></div><footer v-if="item.status === 'pending'"><button type="button" :disabled="workspaceReviewLoading" @click="reviewWorkspaceItem(item.id, 'approved')">确认 Evidence 支持</button><button type="button" :disabled="workspaceReviewLoading" @click="reviewWorkspaceItem(item.id, 'rejected')">不足，继续研究</button></footer></article><p v-if="!workspaceReviews?.length">暂无审核项；没有 Evidence 时系统不会创建虚假审核任务。</p></section>
            <section class="workspace-graph-board"><header><div><p class="section-kicker">EVIDENCE GRAPH LITE</p><h3>Paper → Claim → Decision → Deliverable</h3></div><small>{{ workspaceEvidenceGraph?.nodes?.length || 0 }} nodes</small></header><div class="workspace-graph-flow"><article v-for="node in workspaceEvidenceGraph?.nodes || []" :key="node.id" :class="node.type"><span>{{ node.type }}</span><strong>{{ node.label }}</strong></article></div><p>{{ workspaceEvidenceGraph?.boundary }}</p></section>
            <section class="workspace-deliverable-card"><header><div><p class="section-kicker">DELIVERABLE GENERATOR</p><h3>生成 Evidence-grounded 交付草案</h3></div><div><button type="button" :disabled="workspaceDeliverableLoading" @click="generateWorkspaceDeliverable('literature_review')">Literature Review</button><button type="button" :disabled="workspaceDeliverableLoading" @click="generateWorkspaceDeliverable('project_proposal')">Project Proposal</button><button type="button" :disabled="workspaceDeliverableLoading" @click="generateWorkspaceDeliverable('experiment_plan')">Experiment Plan</button><button type="button" :disabled="workspaceDeliverableLoading" @click="generateResearchBrief">Research Brief</button></div></header><div v-if="workspaceDeliverable" class="workspace-draft"><span>{{ workspaceDeliverable.status }}</span><h4>{{ workspaceDeliverable.title }}</h4><dl><template v-for="(value, key) in workspaceDeliverable.sections" :key="key"><dt>{{ key }}</dt><dd>{{ value }}</dd></template></dl><small>{{ workspaceDeliverable.boundary }}</small></div></section>
          </main>
        </div>
      </section>

      <section v-if="activeWorkspaceView === 'workflow-studio'" class="workflow-studio research-session" aria-label="Research Workflow Studio">
        <header class="dashboard-heading"><div><p class="section-kicker">RESEARCH WORKFLOW STUDIO</p><h2>把研究目标变成可复核的 AI 工作流。</h2><p>计划、执行、Evidence、审核与交付均保留在同一条用户可理解的时间线中。</p></div><button class="outline-button" type="button" @click="openWorkspaceView('tasks')">进入 Research Engine</button></header>
        <p v-if="workflowError" class="error-alert"><span>!</span>{{ workflowError }}</p>
        <section v-if="workflowLoading && !workflowPreview" class="workflow-loading"><span class="spinner"></span><p>AI 正在构建可审阅工作流…</p></section>
        <section v-else-if="!workflowPreview" class="workflow-empty"><b>Workflow Studio</b><p>从 Command Center 输入研究目标，生成第一个工作流预览。</p><button class="primary-card-action" type="button" @click="openWorkspaceView('dashboard')">返回 Command Center</button></section>
        <template v-else><section class="workflow-goal"><span>{{ workflowPreview.workflow_type }}</span><h3>{{ workflowPreview.goal }}</h3><p>{{ workflowPreview.execution_summary || 'AI 已根据研究目标选择可审阅的工作流模板；尚未执行任何研究任务。' }}</p><small>状态：{{ workflowPreview.status }} · 结果：{{ workflowPreview.result_status }}</small></section>
          <section class="workflow-team"><header><p class="section-kicker">AI TEAM RUNTIME</p><h3>Research Mission</h3></header><article v-for="member in workflowPreview.agent_team || []" :key="member.name" :class="member.status"><span>{{ member.name }}</span><b>{{ member.role }}</b><p>{{ member.task }}</p><small>{{ member.status }}{{ member.output ? ' · ' + member.output : '' }}</small></article></section>
          <section class="workflow-timeline"><article v-for="step in workflowPreview.steps" :key="step.id" :class="step.status"><b>{{ String(step.sequence).padStart(2, '0') }}</b><div><span>{{ step.agent_type }}</span><h4>{{ step.step_name }}</h4><p>{{ step.output_reference }}</p></div><aside><strong>{{ step.status }}</strong><small>{{ step.evidence_count }} Evidence</small></aside></article></section>
          <section class="workflow-stream"><header><p class="section-kicker">AI EXECUTION STREAM</p><h3>实际执行事件</h3><button class="text-button" type="button" @click="refreshWorkflowRuntime">刷新</button></header><article v-for="event in workflowPreview.events || []" :key="event.sequence"><b>{{ String(event.sequence).padStart(2, '0') }}</b><div><span>{{ event.agent_name }} · {{ event.phase }}</span><p>{{ event.message }}</p></div><aside><strong>{{ event.status }}</strong><small>{{ event.evidence_count }} Evidence</small></aside></article><p v-if="!(workflowPreview.events || []).length">尚无执行事件。</p></section>
          <section v-if="workflowPreview.sources?.length" class="workflow-evidence"><p class="section-kicker">EVIDENCE REFERENCES</p><article v-for="source in workflowPreview.sources" :key="source.paper_id + source.chunk_id"><b>{{ source.paper_title }}</b><span>{{ source.section }} · {{ source.score }}</span></article></section>
          <section v-if="workflowPreview.copilot" class="workflow-followup"><p class="section-kicker">RESEARCH COPILOT</p><h3>下一步建议</h3><p v-for="item in workflowPreview.copilot.follow_up_suggestions || []" :key="item.title">{{ item.title }}</p><small>{{ workflowPreview.copilot.boundary }}</small></section>
          <footer class="workflow-actions"><p>{{ workflowPreview.timeline_boundary }}</p><button v-if="['CREATED', 'DRAFT'].includes(workflowPreview.status)" class="primary-card-action" type="button" :disabled="workflowLoading" @click="executeResearchWorkflow">{{ workflowLoading ? 'AI Team working…' : 'Start evidence-grounded execution' }}</button><button v-else class="outline-button" type="button" @click="generateResearchWorkflow(workflowPreview.goal)">Generate revised workflow</button></footer></template>
      </section>

      <section v-if="activeWorkspaceView === 'tasks'" class="researchos-task-center research-session" aria-label="AI Research Session">
        <div class="dashboard-heading"><div><p class="section-kicker">AI RESEARCH SESSION</p><h2>把研究问题转化为可复核的研究过程。</h2><p>Research Master 会规划策略、检索真实资料、验证 Evidence，并在需要时保留人工审核。</p></div><button class="outline-button" type="button" @click="openWorkspaceView('assistant')">单篇文献分析</button></div>
        <p v-if="researchOsError" class="error-alert"><span>!</span>{{ researchOsError }}</p>
        <section class="research-command-plan" aria-label="Research Plan">
          <header><div><p class="section-kicker">RESEARCH STRATEGY</p><h3>Research Strategy</h3><small>AI planning before execution</small></div><span :class="(researchOsOverview?.ready_paper_count ?? readyPaperCount) ? 'ready' : 'attention'">{{ (researchOsOverview?.ready_paper_count ?? readyPaperCount) ? (researchOsOverview?.ready_paper_count ?? readyPaperCount) + ' indexed sources' : 'Evidence required' }}</span></header>
          <div class="command-plan-grid"><article><span>Research goal</span><strong>{{ researchCommandPlan.goal }}</strong></article><article><span>Research scope</span><p>{{ researchCommandPlan.scope }}</p></article><article><span>Knowledge sources</span><p>{{ researchCommandPlan.knowledgeStatus }}</p></article><article><span>Expected deliverables</span><p>{{ researchCommandPlan.expected }}</p></article></div>
          <div class="command-plan-details"><section><span>Planned steps</span><ol><li v-for="(step, index) in researchCommandPlan.steps" :key="step"><b>{{ String(index + 1).padStart(2, '0') }}</b>{{ step }}</li></ol></section><section><span>Required tools</span><div class="command-tool-list"><i v-for="tool in researchCommandPlan.tools" :key="tool">{{ tool }}</i></div></section></div>
          <footer v-if="!(researchOsOverview?.ready_paper_count ?? readyPaperCount)"><p>Knowledge base currently contains insufficient evidence. ResearchOS will not produce unsupported research conclusions.</p><button class="outline-button" type="button" @click="openWorkspaceView('knowledge')">Upload research materials</button></footer>
          <footer v-else><p>Research Command will send the goal, selected scope and evidence-backed plan to Research Master. Use Research Worker for a separate controlled execution task.</p><div class="command-footer-actions"><button class="outline-button" type="button" @click="openWorkspaceView('worker')">Open Research Worker</button><button class="primary-card-action" type="button" :disabled="researchOsTaskLoading" @click="runResearchOsTask">Start Research</button></div></footer>
        </section>
        <div class="researchos-task-layout research-session-layout"><section class="task-config-card"><label for="researchos-goal">Research Goal</label><textarea id="researchos-goal" v-model="researchOsGoal" rows="6" placeholder="例如：比较当前资料中的技术路线与验证条件"></textarea><div class="agent-select-heading"><span>参与本次研究的能力</span><button class="text-button" type="button" @click="applyResearchOsDemo">填充比赛案例</button></div><div class="researchos-agent-selector"><button v-for="agent in researchOsAgents" :key="agent.id" type="button" :class="{ active: researchOsSelectedAgents.includes(agent.id) }" @click="toggleResearchOsAgent(agent.id)"><b>{{ agent.name_cn }}</b><small>{{ agent.description }}</small></button></div><button class="analyze-button" type="button" :disabled="researchOsTaskLoading" @click="runResearchOsTask"><span v-if="researchOsTaskLoading" class="spinner small-spinner"></span>{{ researchOsTaskLoading ? 'ResearchOS 正在协作…' : 'Start research session' }}</button></section>
          <section class="researchos-result-card"><div v-if="researchOsTaskLoading" class="loading-state"><span class="spinner"></span><h3>Research Master 正在编排任务</h3><ol class="loading-workflow"><li><i></i>理解科研目标</li><li><i></i>检索团队知识库</li><li><i></i>调度专项 Agent</li><li><i></i>生成科研决策报告</li></ol></div><div v-else-if="!researchOsTaskResult" class="empty-state"><div class="empty-illustration">✦</div><h3>等待科研任务</h3><p>上传相关论文后，输入一个研究目标，获得基于团队知识资产的科研辅助结果。</p></div><div v-else class="researchos-result"><p class="section-kicker">RESEARCH DECISION REPORT</p><h3>科研决策结论</h3><p class="researchos-executive-summary">{{ researchOsTaskResult.executive_summary }}</p><section class="agent-run-board"><h4>Agent 执行状态</h4><article v-for="run in researchOsTaskResult.agent_runs || []" :key="run.agent"><b>✓</b><div><strong>{{ run.agent }}</strong><p>{{ run.message }}</p></div><span>{{ run.status === 'completed' ? '已完成' : run.status }}</span></article></section><details open class="master-plan-card"><summary>Research Master 执行流程</summary><ol><li v-for="step in researchOsTaskResult.master_plan?.workflow_steps || []" :key="step.step"><b>{{ step.step }}</b><div><strong>{{ step.action }}</strong><p>{{ step.agent }} · {{ step.purpose }}</p></div></li></ol></details><section v-for="section in researchOsSections" :key="section[0]" class="researchos-output-section"><h4>{{ section[0] }}</h4><dl><template v-for="(value, key) in section[1]" :key="key"><dt>{{ key }}</dt><dd v-if="Array.isArray(value)"><ul><li v-for="item in value" :key="item">{{ item }}</li></ul></dd><dd v-else>{{ value }}</dd></template></dl></section><details v-if="researchOsTaskResult.sources?.length" class="master-plan-card"><summary>证据来源（{{ researchOsTaskResult.sources.length }}）</summary><article v-for="source in researchOsTaskResult.sources" :key="source.paper_id + source.section"><b>{{ source.paper_title }}</b><span>{{ source.section }} · {{ source.score }}</span><p>{{ source.content }}</p></article></details><p class="trace-boundary">{{ researchOsTaskResult.boundary_note }}</p></div></section><aside class="research-session-evidence"><p class="section-kicker">EVIDENCE SUMMARY</p><h3>研究依据</h3><strong>{{ researchOsTaskResult?.sources?.length || 0 }}</strong><span>条已检索 Evidence</span><p>{{ researchOsTaskResult?.sources?.length ? '本次结果中的来源可在完成后展开查看。' : (readyPaperCount ? '资料已就绪，开始研究后会在此呈现实际引用。' : '当前尚无足够资料；不会生成无依据的研究结论。') }}</p><ul v-if="researchOsTaskResult?.sources?.length"><li v-for="source in researchOsTaskResult.sources.slice(0,3)" :key="source.paper_id + source.section"><b>{{ source.paper_title }}</b><small>{{ source.section || '正文' }}</small></li></ul><button v-if="researchOsTaskResult?.sources?.length" type="button" class="text-button" @click="openWorkspaceView('evidence')">查看 Evidence Center →</button></aside></div>
      </section>

      <section v-if="activeWorkspaceView === 'tasks' && researchOsTaskResult" class="command-run-status" aria-label="Research Command 执行状态">
        <p class="section-kicker">CURRENT RESEARCH COMMAND</p>
        <h3>本次研究指令执行状态</h3>
        <div class="command-run-grid"><article><span>Current goal</span><b>{{ researchOsGoal }}</b></article><article><span>Current status</span><b>{{ researchOsTaskLoading ? 'Running' : 'Completed' }}</b></article><article><span>Evidence count</span><b>{{ researchOsTaskResult.sources?.length || 0 }}</b></article><article><span>Decision status</span><b>{{ researchActions.length ? '待负责人确认' : '可创建行动建议' }}</b></article></div>
        <p><strong>Next recommended action：</strong>{{ researchActions.length ? '前往研究成果中心查看依据并完成人工确认。' : '将有依据的研究建议纳入行动中心，再由负责人确认。' }}</p>
      </section>

          <section v-if="activeWorkspaceView === 'computer'" class="computer-studio computer-agent-workspace" aria-label="AI Worker Computer Skill Workspace">
        <header class="operator-studio-heading computer-operator-heading"><div><p class="section-kicker">AI WORKER · COMPUTER SKILL</p><h2>Controlled Computer Workspace</h2><p>AI Worker 将自然语言任务转为受控执行与人工审批。默认只分析，不自动修改资料或代码。</p></div><span class="operator-status">{{ computerPlanPreview ? 'Plan ready' : (computerTask?.status || 'Ready') }}</span></header>
        <p v-if="computerError" class="error-alert"><span>!</span>{{ computerError }}</p>
        <div class="computer-studio-grid">
          <aside class="operator-task-surface computer-command-surface"><p class="section-kicker">COMPUTER SKILL INPUT</p><h3>What should AI Worker prepare?</h3><textarea v-model="computerGoal" rows="8" @input="computerPlanPreview = null" placeholder="例如：分析当前 ResearchOS 项目代码，找出前端优化点并生成报告"></textarea><label class="computer-mode-label">Execution mode<select v-model="computerMode"><option value="assist">Assist · 只分析</option><option value="supervised">Supervised · 低风险受控执行</option><option value="research">Research · Evidence 绑定交付</option></select></label><button class="analyze-button" type="button" :disabled="computerPlanLoading || !computerGoal.trim()" @click="previewComputerPlan">{{ computerPlanLoading ? 'Building task plan…' : 'Generate skill plan' }}</button><button v-if="computerPlanPreview" class="outline-button computer-start-button" type="button" :disabled="computerLoading" @click="runComputerTask">{{ computerLoading ? 'Executing…' : 'Start controlled execution' }}</button><div class="operator-template-list"><span>SAFE TASKS · 代码修改、文件变更与交付都需审批</span><button type="button" @click="applyComputerTemplate('分析当前 ResearchOS 项目代码，找出前端优化点并生成报告')">分析项目代码</button><button type="button" @click="applyComputerTemplate('整理我的论文目录并生成综述')">整理论文资料</button><button type="button" @click="applyComputerTemplate('优化首页UI')">优化首页 UI</button></div></aside>
          <section class="operator-timeline-surface computer-plan-surface"><header><div><p class="section-kicker">AI WORKER EXECUTION TIMELINE</p><h3>{{ computerPlanPreview?.goal || computerTask?.user_goal || '等待一个受控 Computer Skill 任务' }}</h3></div><small v-if="computerTask || computerPlanPreview">{{ computerPlanPreview?.task_type || computerTask?.task_type }}</small></header><div v-if="computerPlanPreview" class="computer-plan-summary"><span>{{ computerPlanPreview.task_label }}</span><p>{{ computerPlanPreview.expected_output }}</p><small>{{ computerPlanPreview.resource_boundary }}</small></div><ol v-if="(computerPlanPreview?.plan || computerTask?.plan)?.length" class="operator-plan-list"><li v-for="step in (computerPlanPreview?.plan || computerTask?.plan)" :key="step.id || step.step" :class="step.status"><span>{{ String(step.step).padStart(2, '0') }}</span><div><strong>{{ step.task_name || step.action }}</strong><p>{{ step.reason || step.purpose }}</p><small>{{ step.required_tool || step.tool }} · {{ step.evidence_requirement ? 'Evidence required' : 'plan only' }} · {{ step.status }}</small></div></li></ol><div v-else class="operator-empty-state"><b>Understand · Observe · Execute · Recover · Review · Deliver</b><p>Computer Skill 只自动执行白名单只读操作；不会读取私人屏幕、运行任意 shell 或自动修改资料。</p></div><section v-if="computerTask?.events?.length && !computerPlanPreview" class="operator-tool-trace"><h4>Live execution events</h4><article v-for="event in computerTask.events" :key="event.id"><span>Computer Skill · {{ event.event_type }}</span><strong>{{ event.status }}</strong><p>{{ event.message }} <small v-if="event.result_summary">· {{ event.result_summary }}</small></p></article></section><section v-else-if="computerTask?.actions?.length && !computerPlanPreview" class="operator-tool-trace"><h4>Auditable action timeline</h4><article v-for="action in computerTask.actions" :key="action.id"><span>{{ action.tool_name }}</span><strong>{{ action.action_type }} · {{ action.status }}</strong><p>{{ action.result?.message || action.result?.boundary || '已记录受控工具执行摘要。' }}</p></article></section></section>
          <aside class="operator-artifact-surface"><p class="section-kicker">ENVIRONMENT · PERMISSION · APPROVAL</p><h3>Computer status</h3><div v-if="computerTask?.artifact?.artifacts?.length" class="operator-artifact-list"><article v-for="artifact in computerTask.artifact.artifacts" :key="artifact.path"><strong>{{ artifact.format }}</strong><span>{{ artifact.path }}</span></article></div><div class="operator-artifact-empty"><p>{{ computerTask?.artifact?.message || computerPlanPreview?.risk_summary || '计划不会执行工具，也不会创建文档。' }}</p></div><section v-if="computerTask?.checkpoint" class="operator-evidence"><h4>Execution checkpoint</h4><p>{{ computerTask.checkpoint.current_step }} · {{ computerTask.checkpoint.status }}</p><p>{{ computerTask.checkpoint.completed_actions?.length || 0 }} completed · {{ computerTask.checkpoint.remaining_actions?.length || 0 }} pending</p></section><section v-if="computerTask?.patches?.length" class="operator-evidence computer-patch-review"><h4>Patch review</h4><article v-for="patch in computerTask.patches" :key="patch.id"><strong>{{ patch.file_path }} · {{ patch.status }}</strong><pre>{{ patch.diff_content || 'No source change proposed.' }}</pre></article></section><section class="operator-evidence"><h4>Environment</h4><p>Research workspace：{{ computerEnvironment?.workspace?.file_count ?? '—' }} files · {{ computerEnvironment?.workspace?.document_count ?? '—' }} documents</p><p>Project：{{ computerEnvironment?.project?.project_name || '—' }} · {{ computerEnvironment?.project?.technology?.join(' · ') || '未识别' }}</p></section><section class="operator-evidence"><h4>Evidence references</h4><p v-if="!computerTask?.artifact?.evidence_refs?.length">暂无可验证资料；不会生成科研结论。</p><article v-for="ref in computerTask?.artifact?.evidence_refs || []" :key="ref.paper_id + '-' + ref.chunk_id"><strong>{{ ref.paper_title }}</strong><span>{{ ref.section }} · {{ ref.chunk_id }}</span></article></section><section class="computer-memory"><h4>Computer memory</h4><p>{{ computerProCatalog?.memory_boundary || computerMemory?.memory_boundary || '仅保存任务偏好与输出格式，不保存资料正文。' }}</p></section><section class="operator-tools"><h4>Controlled tools</h4><span v-for="tool in computerProCatalog?.tools || computerTools" :key="tool.name">{{ tool.name }}</span></section></aside>
        </div>
        <section class="computer-intelligence-panel computer-environment-timeline" aria-label="Controlled Computer Environment Timeline">
          <header><div><p class="section-kicker">CONTROLLED ENVIRONMENT TIMELINE</p><h3>Environment-aware execution</h3></div><span>{{ computerEnvironment ? 'Environment detected' : 'Awaiting observation' }}</span></header>
          <ol class="computer-control-timeline"><li :class="{ complete: !!computerEnvironment }"><span>01</span><b>Environment</b><small>{{ computerEnvironment ? 'Metadata detected · vision demo only' : 'Awaiting safe observation' }}</small></li><li :class="{ complete: !!computerPlanPreview || !!computerTask }"><span>02</span><b>Action plan</b><small>{{ computerPlanPreview ? 'Controlled plan prepared' : 'No action selected' }}</small></li><li :class="{ complete: computerTask?.status === 'completed', active: computerTask?.status === 'waiting_approval' }"><span>03</span><b>Approval</b><small>{{ computerTask?.status === 'waiting_approval' ? 'Human review required' : 'Approval boundary active' }}</small></li><li :class="{ complete: ['executing','completed'].includes(computerTask?.status) }"><span>04</span><b>Execution</b><small>Controlled actions only</small></li><li :class="{ complete: computerTask?.status === 'completed' }"><span>05</span><b>Verification</b><small>{{ computerTask?.status === 'completed' ? 'Verified' : 'Pending' }}</small></li><li :class="{ active: computerTask?.status === 'needs_review' }"><span>06</span><b>Recovery</b><small>{{ computerTask?.status === 'needs_review' ? 'Human review required' : 'Only if needed' }}</small></li></ol>
        </section>
        <section v-if="computerTask && !computerPlanPreview" class="computer-intelligence-panel" aria-label="Computer Skill Activity Intelligence">
          <header><div><p class="section-kicker">ACTIVITY INTELLIGENCE</p><h3>Explainable execution summary</h3></div><span>{{ computerTask.diffSummary?.impact || 'Workspace analysis' }}</span></header>
          <div v-if="computerTask.mission" class="computer-mission-progress"><div><span>MISSION</span><strong>{{ computerTask.mission.mission_name }}</strong><small>{{ computerTask.mission.current_stage }}</small></div><b>{{ computerTask.mission.progress }}%</b><i><em :style="{ width: computerTask.mission.progress + '%' }"></em></i><p>Computer Skill workflow — source changes remain pending approval.</p></div>
          <div v-if="computerTask.activity?.length" class="computer-activity-list"><article v-for="item in computerTask.activity" :key="item.id"><span>{{ item.stage }}</span><div><strong>{{ item.title }}</strong><p>{{ item.description }}</p></div><small>{{ item.status }}</small></article></div>
          <p v-else class="computer-intelligence-empty">执行开始后，这里只显示用户可理解的分析、计划、变更准备与验证摘要。</p>
          <div v-if="computerTask.diffSummary?.files_changed" class="computer-diff-summary"><strong>{{ computerTask.diffSummary.files_changed }} files changed</strong><span>{{ computerTask.diffSummary.changed_lines }} changed lines · {{ computerTask.diffSummary.risk }} risk</span></div>
          <div v-if="computerTask.codeReview?.length || computerTask.verificationPlan?.length" class="computer-intelligence-meta"><span v-for="review in computerTask.codeReview" :key="review.status">Code review · {{ review.status }}</span><span v-for="check in computerTask.verificationPlan" :key="check.command">{{ check.command }} · {{ check.reason }}</span></div>
        </section>
        <footer v-if="computerTask && !computerPlanPreview" class="operator-approval-bar"><div><p class="section-kicker">HUMAN APPROVAL</p><strong>{{ computerTask.status === 'waiting_approval' ? 'A controlled action is waiting for review.' : computerTask.status }}</strong><span>文件变更、代码 Patch 与交付文件均须确认；外部来源永不自动进入正式 Evidence。</span></div><div v-if="computerTask.status === 'waiting_approval'"><button v-for="action in computerTask.actions.filter((item) => item.status === 'PENDING_APPROVAL')" :key="action.id" class="primary-card-action" type="button" :disabled="computerLoading" @click="reviewComputerAction(action, 'approve')">Approve {{ action.action_type }}</button><button v-for="action in computerTask.actions.filter((item) => item.status === 'PENDING_APPROVAL')" :key="action.id + '-reject'" class="outline-button" type="button" :disabled="computerLoading" @click="reviewComputerAction(action, 'reject')">Reject</button></div></footer>
      </section>

      <section v-if="activeWorkspaceView === 'copilot'" class="computer-studio" aria-label="Research Copilot Action Center">
        <header class="operator-studio-heading"><div><p class="section-kicker">RESEARCH COPILOT</p><h2>AI Activity Center</h2><p>根据真实 Workspace、Evidence 与审核状态提出下一步建议；所有建议均需人工选择。</p></div><span class="operator-status">{{ copilotLoading ? 'Loading' : 'Advisory only' }}</span></header>
        <p v-if="copilotError" class="error-alert"><span>!</span>{{ copilotError }}</p>
        <div v-if="copilotInsight" class="copilot-grid"><section class="operator-task-surface"><p class="section-kicker">RESEARCH CONTEXT</p><h3>{{ copilotInsight.research_goal || '暂无研究目标' }}</h3><p>{{ copilotMemory?.memory_boundary }}</p><small>方向：{{ copilotMemory?.research_direction?.join(' · ') || 'not available' }}</small></section><section class="operator-timeline-surface"><header><div><p class="section-kicker">EVIDENCE INTELLIGENCE</p><h3>Research Readiness {{ copilotInsight.research_readiness?.score ?? '—' }}%</h3></div><small>{{ copilotInsight.research_readiness?.label }}</small></header><div class="copilot-metrics"><article v-for="(value,key) in copilotInsight.research_readiness?.dimensions || {}" :key="key"><span>{{ key.replaceAll('_',' ') }}</span><b>{{ value }}%</b></article></div><h4>Follow-up suggestions</h4><article v-for="item in copilotInsight.follow_up_suggestions || []" :key="item.title" class="copilot-suggestion"><strong>{{ item.title }}</strong><p>{{ item.rationale }}</p><small>{{ item.evidence_refs?.length || 0 }} Evidence references</small><button type="button" class="outline-button" @click="createCopilotSuggestion(item)">Send to review</button></article></section><aside class="operator-artifact-surface"><p class="section-kicker">HUMAN REVIEW QUEUE</p><h3>AI Action Center</h3><article v-for="action in copilotActions" :key="action.id" class="copilot-action"><strong>{{ action.title }}</strong><p>{{ action.rationale }}</p><small>{{ action.evidence_refs?.length || 0 }} Evidence · {{ action.status }}</small><div v-if="action.status==='pending'"><button @click="reviewCopilotAction(action,'approved')">Approve</button><button @click="reviewCopilotAction(action,'rejected')">Reject</button><button @click="reviewCopilotAction(action,'later')">Later</button></div></article><p v-if="!copilotActions.length">暂无待确认建议。</p></aside></div>
        <div v-else class="operator-empty-state"><b>暂无持续研究 Workspace</b><p>完成一次基于 Evidence 的 Research Master 任务后，Copilot 才会提出后续建议。</p></div>
      </section>

      <section v-if="activeWorkspaceView === 'operator'" class="operator-studio" aria-label="Research Operator Studio">
        <header class="operator-studio-heading"><div><p class="section-kicker">CONTROLLED EXECUTION LAYER</p><h2>Operator Studio</h2><p>将科研目标转化为可审计的工具执行与待人工审核交付草稿。</p></div><span class="operator-status">{{ operatorTask?.approval_status === 'pending' ? 'Human review required' : operatorTask?.status || 'Ready' }}</span></header>
        <p v-if="operatorError" class="error-alert"><span>!</span>{{ operatorError }}</p>
        <div class="operator-studio-grid">
          <aside class="operator-task-surface"><p class="section-kicker">TASK</p><h3>What should Research Operator prepare?</h3><textarea v-model="operatorGoal" rows="8" placeholder="例如：根据当前知识库生成 RAG 技术综述"></textarea><button class="analyze-button" type="button" :disabled="operatorLoading || !operatorGoal.trim()" @click="runOperatorTask">{{ operatorLoading ? 'Executing…' : 'Create controlled task' }}</button><div class="operator-template-list"><span>DEMO TASKS · 仅预填任务，不生成虚假结果</span><button type="button" @click="applyOperatorTemplate('根据当前知识库生成RAG技术综述')">RAG 技术综述</button><button type="button" @click="applyOperatorTemplate('设计一个实验验证方案')">实验验证方案</button><button type="button" @click="applyOperatorTemplate('整理我的论文目录')">论文目录整理</button></div></aside>
          <section class="operator-timeline-surface"><header><div><p class="section-kicker">EXECUTION TIMELINE</p><h3>{{ operatorTask?.user_goal || '等待一个受控科研任务' }}</h3></div><small v-if="operatorTask">{{ operatorTask.task_type }}</small></header><ol v-if="operatorTask?.plan?.length" class="operator-plan-list"><li v-for="step in operatorTask.plan" :key="step.step" :class="step.status"><span>{{ String(step.step).padStart(2, '0') }}</span><div><strong>{{ step.action }}</strong><p>{{ step.purpose }}</p><small>{{ step.tool }} · {{ step.status }}</small></div></li></ol><div v-else class="operator-empty-state"><b>Plan · Execute · Review · Deliver</b><p>Research Operator 只调用允许的工具，并在执行涉及交付或文件操作前停在人工审核节点。</p></div><section v-if="operatorTask?.tool_executions?.length" class="operator-tool-trace"><h4>Tool execution</h4><article v-for="item in operatorTask.tool_executions" :key="item.tool_name + item.action"><span>{{ item.tool_name }}</span><strong>{{ item.action }}</strong><p>{{ item.result_summary }}</p></article></section></section>
          <aside class="operator-artifact-surface"><p class="section-kicker">ARTIFACTS & BOUNDARIES</p><h3>Reviewable output</h3><div v-if="operatorTask?.artifact?.artifacts?.length" class="operator-artifact-list"><article v-for="artifact in operatorTask.artifact.artifacts" :key="artifact.path"><strong>{{ artifact.format }}</strong><span>{{ artifact.path }}</span></article></div><div v-else class="operator-artifact-empty"><p>{{ operatorTask?.artifact?.message || '草稿将在 Evidence 可用时生成；资料不足时系统不会输出科研结论。' }}</p></div><section class="operator-evidence"><h4>Evidence references</h4><p v-if="!operatorTask?.evidence_refs?.length">暂无可验证资料</p><article v-for="ref in operatorTask?.evidence_refs || []" :key="ref.paper_id + '-' + ref.chunk_id"><strong>{{ ref.paper_title }}</strong><span>{{ ref.section }}<i v-if="ref.score !== null && ref.score !== undefined"> · {{ ref.score }}</i></span></article></section><section class="operator-tools"><h4>Allowed tools</h4><span v-for="item in operatorTools" :key="item.name">{{ item.name }}</span></section></aside>
        </div>
        <footer v-if="operatorTask" class="operator-approval-bar"><div><p class="section-kicker">HUMAN APPROVAL</p><strong>{{ operatorTask.approval_status === 'pending' ? 'Review the evidence and draft before approving.' : operatorTask.approval_status }}</strong><span>批准不会自动创建 Research Action、Decision 或 Project；文件变更仍需单独授权。</span></div><div v-if="operatorTask.approval_status === 'pending'"><button class="outline-button" type="button" :disabled="operatorLoading" @click="reviewOperatorTask('reject')">Reject</button><button class="primary-card-action" type="button" :disabled="operatorLoading" @click="reviewOperatorTask('approve')">Approve draft</button></div></footer>
      </section>

      <section v-if="activeWorkspaceView === 'worker'" class="worker-workspace" aria-label="Research Worker Workspace">
        <div class="worker-workspace-heading"><div><p class="section-kicker">RESEARCH WORKER</p><h2>Research Worker Workspace</h2><p>AI科研执行助手 · 从科研目标到分析报告的受控执行 Agent。</p></div><div class="worker-status-pill" :class="workerLoading ? 'running' : workerRun?.status || 'ready'"><i></i>{{ workerLoading ? 'Running' : workerRun?.status === 'completed' ? 'Completed' : workerRun?.status === 'need_confirmation' ? 'Need confirmation' : 'Ready' }}<small>ResearchOS · Perfect Release</small></div></div>
        <p v-if="workerError" class="error-alert"><span>!</span>{{ workerError }}</p>
        <div class="worker-workspace-grid"><aside class="worker-task-panel"><p class="section-kicker">TASK INPUT</p><h3>告诉 AI 你需要完成什么科研任务</h3><textarea v-model="workerGoal" rows="8" placeholder="例如：分析上传的实验数据，整理某方向论文或生成实验报告。"></textarea><button class="analyze-button" type="button" :disabled="workerLoading" @click="runResearchWorker"><span v-if="workerLoading" class="spinner small-spinner"></span>{{ workerLoading ? '正在执行…' : '开始执行' }}</button><div class="worker-template-list"><span>快速任务模板</span><button type="button" @click="applyWorkerTemplate('分析上传的实验数据，并输出数据结构与基础统计摘要。')">实验数据分析</button><button type="button" @click="applyWorkerTemplate('整理当前科研工作区中的论文资料，并形成资料执行摘要。')">论文资料整理</button><button type="button" @click="applyWorkerTemplate('基于已索引资料制定待负责人确认的技术路线建议。')">技术路线生成</button><button type="button" @click="applyWorkerTemplate('基于已上传资料生成待人工复核的项目报告。')">项目报告生成</button></div><button class="worker-demo-button" type="button" @click="applyWorkerDemo">一键体验企业科研任务</button></aside>
         <section class="worker-timeline-panel"><div v-if="workerLoading" class="loading-state"><span class="spinner"></span><h3>Research Worker 正在受控执行</h3><ol class="loading-workflow"><li><i></i>理解任务</li><li><i></i>制定计划</li><li><i></i>调用科研工具</li><li><i></i>检查资料依据</li><li><i></i>生成待复核交付物</li></ol></div><div v-else-if="!workerRun" class="worker-empty"><span>✦</span><h3>等待执行任务</h3><p>上传或放入真实科研资料后，输入目标即可开始受控执行。</p></div><div v-else><div class="worker-run-summary"><span>当前任务 · {{ workerRun.current_phase }}</span><h3>{{ workerRun.user_goal }}</h3><p>{{ workerRun.current_step }}</p></div><section v-if="workerTimeline.length" class="worker-loop-timeline"><header><div><p class="section-kicker">AI AGENT LOOP TIMELINE</p><h3>受控执行轨迹</h3></div><span>{{ workerTimeline.length }} steps</span></header><article v-for="(item, index) in workerTimeline" :key="item.timestamp + item.action"><b>{{ index + 1 }}</b><div><span>{{ item.phase }}</span><h4>{{ item.action }}</h4><p>{{ item.result_summary }}</p><small>{{ formatLibraryDate(item.timestamp) }}</small></div><i>completed</i></article></section><div class="execution-card"><header><b>1</b><div><span>Task Understanding</span><h4>任务理解</h4></div><em>Completed</em></header><p>AI 已接收科研执行目标，并限定在允许的科研工具范围内。</p></div><div class="execution-card"><header><b>2</b><div><span>Planning</span><h4>任务规划</h4></div><em>{{ workerRun.plan?.length ? 'Completed' : 'Pending' }}</em></header><ol><li v-for="item in workerRun.plan || []" :key="item.step"><strong>{{ item.action }}</strong><small>{{ item.reason || item.selection_reason }}</small><i :class="item.status">{{ item.status }}</i></li></ol></div><div class="execution-card"><header><b>3</b><div><span>Tool Calling</span><h4>工具调用</h4></div><em>{{ workerRun.tools?.length || 0 }} tools</em></header><div class="worker-tool-pills"><span v-for="tool in workerRun.tools || []" :key="tool.name">✓ {{ tool.name }}</span></div></div><div class="execution-card"><header><b>4</b><div><span>Observation</span><h4>结果观察</h4></div><em>{{ workerRun.result?.file_tool?.asset_count || 0 }} files</em></header><p>资料：{{ workerRun.result?.file_tool?.asset_count || 0 }} 个 · RAG 证据：{{ workerRun.result?.knowledge_tool?.source_count || 0 }} 条 · 数据集：{{ workerRun.result?.data_tool?.dataset_count || 0 }} 个</p></div><div class="execution-card"><header><b>5</b><div><span>Reflection</span><h4>结果评估</h4></div><em>{{ workerRun.reflection?.has_verifiable_material ? 'Ready for review' : 'Need material' }}</em></header><p>{{ workerRun.reflection?.message || workerRun.reflection?.result_check || '正在等待结果评估。' }}</p><small>{{ workerRun.reflection?.next_step || workerRun.reflection?.suggestion }}</small></div><div class="execution-card delivery-card"><header><b>6</b><div><span>Delivery</span><h4>最终交付</h4></div><em>{{ workerRun.status }}</em></header><p v-if="workerRun.output_file">已生成本地报告：<code>{{ workerRun.output_file }}</code></p><p v-else>尚未生成交付物。资料不足时系统不会伪造报告。</p><p class="trace-boundary">{{ workerRun.reflection?.human_review }}</p></div></div></section>
      <section v-if="activeWorkspaceView === 'worker' && workerRun" class="worker-review-center" aria-label="AI科研执行审核中心">
        <p class="section-kicker">HUMAN REVIEW</p><h3>AI科研执行审核中心</h3>
        <p>先核验资料与 Evidence，再决定是否采纳建议。此处只记录审核意图，不会自动创建 Action。</p>
        <div class="worker-review-evidence"><b>证据来源（{{ workerRun.result?.knowledge_tool?.source_count || 0 }}）</b>
          <p v-if="!(workerRun.result?.knowledge_tool?.sources || []).length">暂无可验证资料</p>
          <article v-for="(source, index) in workerRun.result?.knowledge_tool?.sources || []" :key="index"><strong>{{ source.paper_title || source.source || '未命名资料' }}</strong><small>{{ source.section || source.chapter || '未标注章节' }} · 匹配度：{{ source.score || '未提供' }}</small></article>
        </div>
        <label>修改说明（可选）<textarea v-model="workerReviewNote" rows="2" placeholder="记录需人工补充或调整的内容"></textarea></label>
        <div class="worker-review-actions"><button type="button" :class="{ selected: workerReviewDecision === 'accepted' }" @click="reviewResearchWorker('accepted')">接受建议</button><button type="button" :class="{ selected: workerReviewDecision === 'modified' }" @click="reviewResearchWorker('modified')">修改建议</button><button type="button" :class="{ selected: workerReviewDecision === 'rejected' }" @click="reviewResearchWorker('rejected')">驳回建议</button></div>
        <p v-if="workerReviewDecision" class="review-result">已记录人工审核：{{ workerReviewDecision === 'accepted' ? '接受建议' : workerReviewDecision === 'modified' ? '修改后接受' : '驳回建议' }}。请在现有决策闭环中由负责人创建后续 Action。</p>
      </section>
          <aside class="worker-control-panel"><p class="section-kicker">AGENT CONTROL PANEL</p><h3>Research Worker</h3><div class="worker-control-status"><span>状态</span><b>{{ workerLoading ? 'Running' : workerRun?.status || 'Ready' }}</b></div><div class="worker-control-status"><span>当前任务</span><p>{{ workerRun?.user_goal || workerGoal }}</p></div><section><h4>可用工具</h4><ul><li v-for="tool in workerTools" :key="tool.name"><b>✓</b><div><strong>{{ tool.name }}</strong><small>{{ tool.description }}</small></div></li></ul></section><section class="worker-safety"><h4>安全边界</h4><p>✓ 不修改原始数据</p><p>✓ 不生成无依据科研结论</p><p>✓ 所有结果需人工确认</p></section><section class="worker-demo-flow"><h4>企业科研任务演示</h4><ol><li>企业需求</li><li>任务拆解</li><li>知识检索</li><li>数据分析</li><li>技术路线</li><li>成果报告</li></ol></section></aside></div>
      <section v-if="activeWorkspaceView === 'workspace'" class="enterprise-center">
        <div class="dashboard-heading"><div><p class="section-kicker">RESEARCH WORKSPACE</p><h2>Research Workspace</h2><p>面向实验室与企业协作的轻量工作空间。角色用于界面展示，不代表已启用登录权限。</p></div></div>
        <p v-if="workspaceError" class="error-alert"><span>!</span>{{ workspaceError }}</p>
        <form class="workspace-create" @submit.prevent="createResearchWorkspace"><input v-model="workspaceName" placeholder="输入实验室或企业工作空间名称" /><button class="primary-card-action" :disabled="workspaceLoading">创建工作空间</button></form>
        <div class="workspace-card-grid"><article v-for="space in workspaces" :key="space.id" :class="{ active: activeResearchWorkspace?.id === space.id }" @click="activeResearchWorkspace = space; loadResearchTasks()"><span>WORKSPACE</span><h3>{{ space.name }}</h3><p>{{ space.member_roles.join(' · ') }}</p><div><b>{{ space.document_count }}</b><small>资料</small><b>{{ space.project_count }}</b><small>项目</small><b>{{ space.agent_execution_count }}</b><small>Agent执行</small></div></article><div v-if="!workspaces.length && !workspaceLoading" class="workspace-empty">暂无工作空间。创建一个空间以组织任务、项目和交付记录。</div></div>
      </section>

      <section v-if="activeWorkspaceView === 'task-center'" class="enterprise-center">
        <div class="dashboard-heading"><div><p class="section-kicker">RESEARCH TASK CENTER</p><h2>科研任务中心</h2><p>将文献、数据、企业需求与技术路线规划，关联到已有 Research Worker 执行记录。</p></div><button class="outline-button" @click="loadResearchTasks">刷新任务</button></div>
        <p v-if="!activeResearchWorkspace" class="demo-boundary">请先创建或选择 Research Workspace。</p>
        <form v-else class="task-create" @submit.prevent="createResearchTask"><input v-model="taskName" placeholder="任务名称" /><select v-model="taskType"><option>文献分析</option><option>数据分析</option><option>企业需求分析</option><option>技术路线规划</option></select><button class="primary-card-action" :disabled="taskCenterLoading">创建任务</button></form>
        <div class="task-board"><article v-for="item in researchTasks" :key="item.id"><span :class="item.status">{{ item.status }}</span><h3>{{ item.name }}</h3><p>{{ item.task_type }} · Evidence {{ item.evidence_count }} 条</p><small>{{ item.output_report || '尚未关联输出报告' }}</small></article><p v-if="!researchTasks.length && activeResearchWorkspace">暂无任务。可从当前 Worker 执行结果创建任务。</p></div>
      </section>

      <section v-if="activeWorkspaceView === 'delivery-center'" class="enterprise-center">
        <div class="dashboard-heading"><div><p class="section-kicker">CLIENT DELIVERY CENTER</p><h2>企业交付报告中心</h2><p>将已有 Worker 结果汇总为可沟通的交付摘要。</p></div><button class="primary-card-action" :disabled="!workerRun || deliveryLoading" @click="loadClientDelivery">生成交付预览</button></div>
        <div v-if="!workerRun" class="workspace-empty">请先完成一项 Research Worker 任务，再生成企业交付摘要。</div>
        <div v-else-if="deliveryPreview" class="delivery-board"><header><span>AI辅助生成 · 需人工审核</span><h3>{{ deliveryPreview.client_requirement }}</h3></header><section><b>已有资料</b><p>文件 {{ deliveryPreview.ai_analysis.available_files }} 个 · Evidence {{ deliveryPreview.ai_analysis.evidence_count }} 条</p></section><section><b>交付物</b><ul><li v-for="item in deliveryPreview.deliverables" :key="item">{{ item }}</li></ul></section><section><b>Evidence</b><p v-if="!deliveryPreview.evidence?.length">暂无可验证资料</p><ul v-else><li v-for="(item,index) in deliveryPreview.evidence" :key="index">{{ item.paper_title || item.source }} · {{ item.section || item.chapter }}</li></ul></section><footer>{{ deliveryPreview.boundary_note }}</footer><button class="outline-button" :disabled="deliveryLoading" @click="exportClientDelivery">Export Report（PDF）</button></div>
      </section>

      <section v-if="activeWorkspaceView === 'agent-monitor'" class="enterprise-center">
        <div class="dashboard-heading"><div><p class="section-kicker">AGENT MONITOR</p><h2>Agent 能力监控</h2><p>仅显示执行记录、状态与工具调用次数；不显示 Token、Prompt 或思维链。</p></div><button class="outline-button" @click="loadAgentMonitor">刷新监控</button></div>
        <div v-if="agentMonitor" class="monitor-grid"><article v-for="agent in agentMonitor.agents" :key="agent.name"><span>{{ agent.name }}</span><h3>{{ agent.execution_count }} 次执行</h3><p>成功 {{ agent.success_tasks }} · 失败 {{ agent.failed_tasks }}</p><small>平均耗时：{{ agent.average_duration_seconds === null ? '暂无数据' : agent.average_duration_seconds + ' 秒' }}</small></article></div><div v-if="agentMonitor" class="tool-monitor"><b>工具调用</b><span v-for="tool in agentMonitor.tool_calls" :key="tool.name">{{ tool.name }} · {{ tool.count }}</span><p>{{ agentMonitor.boundary }}</p></div>
      </section>

      </section>

      <section v-if="activeWorkspaceView === 'worker' && workerRun" class="tool-trace-center" aria-label="Tool Execution Trace">
        <div class="dashboard-heading"><div><p class="section-kicker">TOOL EXECUTION TRACE</p><h2>受控工具执行轨迹</h2><p>来自当前 Research Worker 的用户可读执行记录，不展示 Prompt、Token 或模型思维链。</p></div></div>
        <div class="tool-trace-board"><article v-for="(item,index) in workerTimeline" :key="item.timestamp + index"><b>0{{ index + 1 }}</b><div><span>当前阶段：{{ item.phase || '未标注' }}</span><h3>{{ item.tool || item.module || item.action }}</h3><p><strong>调用原因：</strong>{{ item.action || '执行既定受控任务' }}</p><p><strong>输入摘要：</strong>{{ item.input_summary || '当前 Worker 运行上下文' }}</p><p><strong>输出摘要：</strong>{{ item.result_summary || '暂无输出摘要' }}</p><small>Evidence：{{ item.evidence_count || 0 }} · {{ formatLibraryDate(item.timestamp) }}</small></div><em>completed</em></article><p v-if="!workerTimeline.length" class="workspace-empty">当前运行尚未返回可展示的工具轨迹。</p></div>
      </section>

      <section v-if="activeWorkspaceView === 'enterprise-hub'" class="enterprise-hub enterprise-center" aria-label="Enterprise Command Center">
        <header class="dashboard-heading"><div><p class="section-kicker">ENTERPRISE COMMAND CENTER</p><h2>团队研究协作空间</h2><p>将成员、项目、共享知识、审核活动与交付状态连接在同一组织视图中。</p></div><button v-if="enterpriseOrganization" class="outline-button" type="button" :disabled="enterpriseLoading" @click="loadEnterpriseHub">{{ enterpriseLoading ? '同步中…' : '刷新组织数据' }}</button></header>
        <p v-if="enterpriseError" class="error-alert"><span>!</span>{{ enterpriseError }}</p>
        <section v-if="!enterpriseOrganization" class="enterprise-onboarding"><p class="section-kicker">ORGANIZATION WORKSPACE</p><h3>创建首个组织协作空间</h3><p>仅创建本地 Organization 与管理员成员，不会生成项目、科研资料或 Evidence。</p><input v-model="enterpriseOrgName" placeholder="组织名称，例如：先进材料实验室" /><input v-model="enterpriseAdminName" placeholder="管理员显示名" /><button class="primary-card-action" type="button" :disabled="enterpriseLoading" @click="createEnterpriseOrganization">{{ enterpriseLoading ? '创建中…' : '创建 Organization' }}</button></section>
        <template v-else>
          <section class="enterprise-summary-grid"><article><span>ORGANIZATION</span><b>{{ enterpriseDashboard?.organization?.name || enterpriseOrganization.name }}</b><small>{{ enterpriseDashboard?.organization?.member_count || enterpriseMembers.length }} 成员</small></article><article><span>PROJECTS</span><b>{{ enterpriseDashboard?.projects?.total || 0 }}</b><small>真实组织级项目</small></article><article><span>EVIDENCE</span><b>{{ enterpriseDashboard?.evidence_count || 0 }}</b><small>来自已授权知识资料</small></article><article><span>REVIEW QUEUE</span><b>{{ enterpriseDashboard?.review_queue || 0 }}</b><small>待团队人工审核</small></article><article><span>DELIVERABLES</span><b>{{ enterpriseDashboard?.deliverable_progress || 0 }}</b><small>已记录草稿版本</small></article></section>
          <div class="enterprise-hub-grid"><section class="enterprise-project-panel"><p class="section-kicker">PROJECT CENTER</p><h3>企业项目</h3><div class="enterprise-project-create"><input v-model="enterpriseProjectName" placeholder="项目名称" /><textarea v-model="enterpriseProjectGoal" rows="3" placeholder="研究目标（可选）"></textarea><button class="outline-button" type="button" :disabled="enterpriseLoading || !enterpriseProjectName.trim()" @click="createEnterpriseProject">创建项目</button></div><article v-for="project in enterpriseProjects" :key="project.id" class="enterprise-project-item"><span>{{ project.status }}</span><h4>{{ project.name }}</h4><p>{{ project.research_goal || '尚未补充研究目标。' }}</p><footer><small>{{ project.owner }} · {{ project.member_count }} 成员</small><small>{{ project.evidence_count }} Evidence · {{ project.task_count }} 任务</small><small>{{ project.review_status }} · {{ project.deliverable_status }}</small></footer></article><div v-if="!enterpriseProjects.length" class="enterprise-empty">尚无企业项目。创建项目后再关联既有 Workspace、Evidence 与交付物。</div></section>
            <section class="enterprise-activity-panel"><p class="section-kicker">RESEARCH ACTIVITY</p><h3>团队动态</h3><ol><li v-for="item in enterpriseActivity" :key="item.timestamp + item.action"><b>{{ item.actor }}</b><span>{{ item.role }} · {{ item.action }}</span><p>{{ item.target }}</p><small>{{ formatLibraryDate(item.timestamp) }}</small></li></ol><div v-if="!enterpriseActivity.length" class="enterprise-empty">尚无组织活动记录。</div></section>
            <aside class="enterprise-insight-panel"><p class="section-kicker">TEAM KNOWLEDGE</p><h3>共享资料</h3><article v-for="item in enterpriseKnowledge" :key="item.paper_id"><b>{{ item.title }}</b><span>{{ item.knowledge_scope }} · {{ item.chunk_count }} Chunks</span></article><p v-if="!enterpriseKnowledge.length">尚无已授权共享资料。资料可在既有 Knowledge Core 上传后，由有权限的成员设置范围。</p><hr /><p class="section-kicker">MEETING ASSISTANT</p><h3>会议提案</h3><textarea v-model="enterpriseMeetingNotes" rows="5" placeholder="输入会议纪要；系统只生成待人工确认的决策与行动项。"></textarea><button class="outline-button" type="button" :disabled="enterpriseLoading || !enterpriseMeetingNotes.trim()" @click="createEnterpriseMeeting">生成待确认提案</button><div v-if="enterpriseMeeting" class="meeting-proposal"><b>{{ enterpriseMeeting.summary }}</b><small>决策和行动项均为 pending，未自动创建正式任务。</small></div><hr /><p class="section-kicker">FDE DELIVERY PACKAGE</p><button class="outline-button" type="button" :disabled="enterpriseLoading" @click="loadEnterpriseDeliveryPackage">生成待审核交付包</button><div v-if="enterpriseDeliveryPackage" class="meeting-proposal"><b>{{ enterpriseDeliveryPackage.status }}</b><small>{{ enterpriseDeliveryPackage.data_boundary }}</small></div></aside>
          </div>
          <section class="enterprise-flow"><span>Leader 创建项目</span><i>→</i><span>Researcher 共享资料</span><i>→</i><span>AI 整理 Evidence</span><i>→</i><span>Reviewer 审核</span><i>→</i><span>Leader 确认交付</span></section>
        </template>
      </section>

      <section v-if="activeWorkspaceView === 'fde-solution-studio'" class="fde-solution-studio enterprise-center" aria-label="FDE Solution Studio">
        <header class="dashboard-heading">
          <div><p class="section-kicker">FDE SOLUTION STUDIO</p><h2>From customer need to delivery-ready solution.</h2><p>将客户需求转化为可审核的解决方案草稿；需求、风险与交付内容均需人工确认。</p></div>
          <button class="outline-button" type="button" @click="applyFdeSolutionDemo">Load DEMO scenario</button>
        </header>
        <p v-if="fdeSolutionError" class="error-alert"><span>!</span>{{ fdeSolutionError }}</p>
        <div class="fde-solution-layout">
          <section class="fde-need-surface">
            <p class="section-kicker">CUSTOMER NEED</p><h3>Start with a real need.</h3>
            <label>Solution title<input v-model="fdeSolutionForm.title" placeholder="例如：科研知识智能平台建设方案" /></label>
            <label>Industry<input v-model="fdeSolutionForm.industry" placeholder="Higher Education / Enterprise R&D" /></label>
            <label>Customer need<textarea v-model="fdeSolutionForm.customer_need" rows="7" placeholder="描述客户需要解决的问题、已有资料和目标。"></textarea></label>
            <label>Business objective<textarea v-model="fdeSolutionForm.objective" rows="3" placeholder="可选：本次方案希望达成的目标。"></textarea></label>
            <button class="primary-card-action" type="button" :disabled="fdeSolutionLoading" @click="createFdeSolution">{{ fdeSolutionLoading ? 'Working…' : 'Create solution draft' }}</button>
            <small>DEMO 场景只用于演示，不能视为真实客户确认或真实客户资料。</small>
            <div v-if="fdeSolutions.length" class="fde-existing-solutions"><span>RECENT DRAFTS</span><button v-for="item in fdeSolutions" :key="item.id" type="button" :class="{ active: selectedFdeSolution?.id === item.id }" @click="loadFdeSolutionDetail(item.id)"><b>{{ item.title }}</b><small>{{ item.status }} · {{ item.review_status }}</small></button></div>
          </section>
          <section class="fde-pipeline-surface">
            <template v-if="selectedFdeSolution">
              <header><div><p class="section-kicker">SOLUTION PIPELINE</p><h3>{{ selectedFdeSolution.title }}</h3><small>{{ selectedFdeSolution.status }} · Review {{ selectedFdeSolution.review_status }}</small></div><button class="text-button" type="button" @click="loadFdeSolutions">Refresh</button></header>
              <ol class="fde-pipeline">
                <li :class="{ active: !!selectedFdeSolution.requirements?.length }"><b>01</b><div><strong>Requirement Understanding</strong><p>{{ selectedFdeSolution.requirements?.length || 0 }} draft requirements · {{ selectedFdeSolution.requirements?.length ? 'Needs confirmation' : 'Awaiting analysis' }}</p><button class="outline-button" type="button" :disabled="fdeSolutionLoading" @click="analyzeFdeSolution">Analyze requirements</button></div></li>
                <li :class="{ active: !!fdeSolutionBlueprint || !!selectedFdeSolution.deliverables?.length }"><b>02</b><div><strong>Architecture & blueprint</strong><p>仅映射 ResearchOS 已有能力；不会虚构技术组件或资料。</p><button class="outline-button" type="button" :disabled="fdeSolutionLoading || !selectedFdeSolution.requirements?.length" @click="generateFdeSolutionBlueprint">Generate blueprint</button></div></li>
                <li :class="{ active: !!selectedFdeSolution.deliverables?.length }"><b>03</b><div><strong>Risk & human review</strong><p>高风险和未确认需求必须由负责人判断，不自动批准。</p><textarea v-model="fdeSolutionReviewNote" rows="2" placeholder="审核说明（可选）"></textarea><div><button class="outline-button" type="button" :disabled="fdeSolutionLoading" @click="reviewFdeSolution('NEEDS_REVISION')">Needs revision</button><button class="primary-card-action" type="button" :disabled="fdeSolutionLoading" @click="reviewFdeSolution('APPROVED')">Approve review</button></div></div></li>
                <li :class="{ active: !!fdeSolutionPackage }"><b>04</b><div><strong>Delivery package</strong><p>仅在人工审核批准后生成；不会自动构成正式客户交付。</p><button class="outline-button" type="button" :disabled="fdeSolutionLoading || selectedFdeSolution.review_status !== 'APPROVED'" @click="loadFdeSolutionPackage">Open delivery package</button><small v-if="selectedFdeSolution.review_status !== 'APPROVED'">Human Review approval required</small></div></li>
              </ol>
              <section v-if="fdeSolutionAnalysis" class="fde-analysis-summary"><p class="section-kicker">REQUIREMENT INTELLIGENCE</p><div v-for="item in fdeSolutionAnalysis.requirements || []" :key="item.id"><b>{{ item.requirement_type }}</b><span>{{ item.description }}</span><small>{{ item.priority }} · {{ item.status }}</small></div><p>{{ fdeSolutionAnalysis.gap_analysis?.summary || '所有需求均为待确认的 AI 结构化理解。' }}</p></section>
              <section v-if="fdeSolutionBlueprint" class="fde-blueprint-summary"><p class="section-kicker">SOLUTION INTELLIGENCE</p><div class="fde-metric-strip"><span>Requirements <b>{{ fdeSolutionBlueprint.metrics?.requirements_parsed || 0 }}</b></span><span>Evidence linked <b>{{ fdeSolutionBlueprint.metrics?.evidence_linked || 0 }}</b></span><span>Risks <b>{{ fdeSolutionBlueprint.metrics?.risks_identified || 0 }}</b></span><span>Drafts <b>{{ fdeSolutionBlueprint.metrics?.deliverables_generated || 0 }}</b></span></div><p>{{ fdeSolutionBlueprint.blueprint?.boundary }}</p><ul><li v-for="risk in fdeSolutionBlueprint.blueprint?.risks || []" :key="risk.code"><b>{{ risk.level }}</b> {{ risk.title }} · {{ risk.action }}</li></ul></section>
            </template>
            <div v-else class="product-empty-state"><b>No solution project selected</b><p>Enter a customer need or load the labeled DEMO scenario to begin a reviewable FDE solution draft.</p></div>
          </section>
          <aside class="fde-intelligence-surface">
            <p class="section-kicker">SOLUTION INTELLIGENCE</p><h3>Evidence and controls.</h3>
            <article><span>Evidence boundary</span><b>{{ selectedFdeSolution?.metrics?.evidence_linked || fdeSolutionBlueprint?.metrics?.evidence_linked || 0 }}</b><small>只关联当前知识库中可追溯的 paper / chunk 引用。</small></article>
            <article><span>Review status</span><b>{{ selectedFdeSolution?.review_status || 'PENDING' }}</b><small>AI 不会确认客户需求、风险或正式交付。</small></article>
            <article><span>Delivery status</span><b>{{ fdeSolutionPackage?.status || selectedFdeSolution?.status || 'DRAFT' }}</b><small>所有包内容保留 AI Generated Draft 标记。</small></article>
            <section class="fde-evidence-list"><span>EVIDENCE REFERENCES</span><p v-if="!fdeEvidenceRefs().length">暂无可验证资料</p><article v-for="item in fdeEvidenceRefs()" :key="item.chunk_id"><b>{{ item.source }}</b><small>paper_id: {{ item.paper_id }} · chunk_id: {{ item.chunk_id }}</small><small>{{ item.section || '正文' }}</small></article></section>
            <section class="fde-computer-mission"><span>COMPUTER MISSION</span><p v-if="!fdeComputerMissions.length">Blueprint 生成后会创建受控行动提案。</p><article v-for="item in fdeComputerMissions" :key="item.id"><b>{{ item.status }}</b><small>{{ item.task }}</small><p>{{ item.change_summary }}</p><em>Proposal only · no execution</em></article></section>
            <section class="fde-version-control"><span>SOLUTION VERSION CONTROL</span><p v-if="!fdeSolutionVersions.length">生成 Blueprint 后保留可审阅版本。</p><article v-for="item in fdeSolutionVersions" :key="item.id"><b>V{{ item.version }} · {{ item.status }}</b><small>{{ item.change_summary }}</small></article></section>
            <button class="text-button" type="button" @click="openWorkspaceView('computer')">Check capability in Computer Lab →</button>
          </aside>
        </div>
        <section v-if="fdeSolutionPackage" class="fde-delivery-package"><header><div><p class="section-kicker">FDE DELIVERY PACKAGE</p><h3>{{ fdeSolutionPackage.label || 'AI Generated Draft · NEEDS_CONFIRMATION' }}</h3></div><span>{{ selectedFdeSolution?.review_status || 'PENDING' }}</span></header><p>{{ fdeSolutionPackage.boundary || 'This package is an AI generated draft. Customer and reviewer confirmation are required before formal delivery.' }}</p><div><b>Executive summary</b><p>{{ fdeSolutionPackage.executive_summary }}</p></div><div><b>Customer problem</b><p>{{ fdeSolutionPackage.customer_problem }}</p></div><div><b>Implementation roadmap</b><ul><li v-for="item in fdeSolutionPackage.implementation_roadmap?.content || []" :key="item.phase">Phase {{ item.phase }} · {{ item.name }} — {{ item.goal }}</li></ul></div><div><b>Risk & security</b><ul><li v-for="item in fdeSolutionPackage.risk_and_security || []" :key="item.type"><strong>{{ item.level }}</strong> · {{ item.reason }} — {{ item.recommendation }}</li></ul></div><div><b>Acceptance criteria</b><ul><li v-for="item in fdeSolutionPackage.acceptance_criteria || []" :key="item">{{ item }}</li></ul></div><div><b>Next steps</b><ul><li v-for="item in fdeSolutionPackage.next_steps || []" :key="item">{{ item }}</li></ul></div></section>
      </section>

      <section v-if="activeWorkspaceView === 'solution-delivery'" class="solution-delivery-workspace enterprise-center" aria-label="P5 Solution Delivery Layer">
        <header class="dashboard-heading"><div><p class="section-kicker">RESEARCHOS FOR TEAMS</p><h2>AI Research Solution Delivery</h2><p>用真实运行状态、客户场景模板与可审计边界组织研究团队的 AI 解决方案；不创建客户数据、不承诺未验证收益。</p></div><button class="primary-card-action" type="button" @click="startSolutionDemo">Start demo</button></header>
        <p v-if="solutionError" class="error-alert"><span>!</span>{{ solutionError }}</p>
        <div v-if="solutionLoading && !solutionScenarios.length" class="workspace-empty"><span class="spinner"></span><p>正在读取方案模板与真实运行概览…</p></div>
        <template v-else>
          <section class="solution-scenario-tabs"><button v-for="item in solutionScenarios" :key="item.scenario_id" type="button" :class="{ active: selectedSolutionScenario === item.scenario_id }" @click="selectSolutionScenario(item.scenario_id)"><span>DEMO SCENARIO</span><b>{{ item.name }}</b><small>{{ item.customer_type }}</small></button></section>
          <section v-if="solutionBlueprint" class="solution-blueprint-card"><div><p class="section-kicker">SOLUTION BLUEPRINT</p><h3>{{ solutionBlueprint.scenario.name }}</h3><p>客户问题 → AI 方案 → 技术架构 → 交付过程 → 预期结果</p></div><div class="solution-blueprint-flow"><article><span>Customer Problem</span><b>{{ solutionBlueprint.customer_problem[0] }}</b></article><i>→</i><article><span>AI Solution</span><b>{{ solutionBlueprint.ai_solution.join(' · ') }}</b></article><i>→</i><article><span>Delivery Process</span><b>{{ solutionBlueprint.delivery_process.slice(0, 2).join(' · ') }}</b></article></div><small>{{ solutionBlueprint.boundary }}</small></section>
          <section class="solution-admin-grid"><article><p>Workspaces</p><strong>{{ solutionAdminOverview?.workspace_count ?? 0 }}</strong><span>真实本地工作空间</span></article><article><p>Research Tasks</p><strong>{{ solutionAdminOverview?.research_task_count ?? 0 }}</strong><span>真实任务记录</span></article><article><p>Evidence</p><strong>{{ solutionAdminOverview?.evidence_count ?? 0 }}</strong><span>真实知识片段</span></article><article><p>Pending Review</p><strong>{{ solutionAdminOverview?.review_status?.pending ?? 0 }}</strong><span>待人工审核</span></article></section>
          <section v-if="solutionRoi" class="solution-roi-board"><header><div><p class="section-kicker">POTENTIAL VALUE INDICATORS</p><h3>价值与资产概览</h3><p>展示可观察资产与可用于评估的价值维度，不将其标注为已实现 ROI。</p></div><span>Potential</span></header><div class="solution-roi-assets"><article v-for="(value,key) in solutionRoi.research_assets" :key="key"><span>{{ key.replaceAll('_',' ') }}</span><b>{{ value }}</b></article></div><div class="solution-value-list"><article v-for="item in solutionRoi.potential_value_indicators" :key="item.name"><b>{{ item.name }}</b><p>{{ item.detail }}</p></article></div><small>{{ solutionRoi.research_topic_coverage?.detail }} {{ solutionRoi.boundary }}</small></section>
          <section v-if="solutionDemoFlow" class="solution-demo-flow"><header><div><p class="section-kicker">DEMO PRESENTATION MODE</p><h3>RAG 技术方向 · 六步演示</h3><p>演示步骤为方案说明；Evidence 数和审核状态由只读 Demo Flow 的真实运行概览提供。</p></div><span>Step {{ solutionDemoStep + 1 }} / {{ solutionDemoFlow.steps.length }}</span></header><ol><li v-for="(item,index) in solutionDemoFlow.steps" :key="item.step" :class="{ active: solutionDemoStep === index, done: solutionDemoStep > index }" @click="solutionDemoStep = index"><b>0{{ item.step }}</b><div><strong>{{ item.title }}</strong><small>状态：{{ solutionDemoStep > index ? 'Demo 已讲解' : solutionDemoStep === index ? '当前步骤' : '待演示' }} · Evidence：{{ item.evidence_count }} · Review：{{ item.review_status === 'pending_review' ? '待审核' : '暂无待审核项' }}</small></div></li></ol><footer><button class="outline-button" :disabled="solutionDemoStep === 0" @click="solutionDemoStep--">上一步</button><button class="primary-card-action" :disabled="solutionDemoStep >= solutionDemoFlow.steps.length - 1" @click="solutionDemoStep++">下一步</button></footer><small>{{ solutionDemoFlow.boundary }}</small></section>
          <section v-if="solutionDeliveryReport" class="solution-customer-report"><header><span>AI辅助生成 · 需客户确认</span><h3>{{ solutionDeliveryReport.title }}</h3></header><article><h4>Customer Background</h4><p>{{ solutionDeliveryReport.customer_background }}</p></article><article><h4>Requirement Analysis</h4><ul><li v-for="item in solutionDeliveryReport.requirement_analysis" :key="item">{{ item }}</li></ul></article><article><h4>Solution Design</h4><ul><li v-for="item in solutionDeliveryReport.solution_design" :key="item">{{ item }}</li></ul></article><article><h4>Implementation Process</h4><ol><li v-for="item in solutionDeliveryReport.implementation_process" :key="item">{{ item }}</li></ol></article><article><h4>Validation Result</h4><ul><li v-for="item in solutionDeliveryReport.validation_result" :key="item">{{ item }}</li></ul></article><article><h4>Future Optimization</h4><ul><li v-for="item in solutionDeliveryReport.future_optimization" :key="item">{{ item }}</li></ul></article><footer>{{ solutionDeliveryReport.boundary }}</footer></section>
        </template>
      </section>

      <section v-if="activeWorkspaceView === 'fde-config'" class="fde-config-center enterprise-center" aria-label="FDE Configuration Center">
        <div class="dashboard-heading"><div><p class="section-kicker">FDE CONFIGURATION CENTER · DEMO</p><h2>FDE 配置中心</h2><p>为客户场景生成实施方案、模块映射和验收标准；不会自动修改真实系统。</p></div></div>
        <div class="fde-config-grid"><section><label>客户类型<select v-model="fdeClientType"><option>高校实验室</option><option>企业研发中心</option><option>产学研平台</option></select></label><h3>需求配置</h3><button v-for="item in ['知识库建设','文献管理','数据分析','技术路线规划','成果管理']" :key="item" type="button" :class="{ active: fdeSelectedNeeds.includes(item) }" @click="toggleFdeNeed(item)">{{ item }}</button><button class="primary-card-action" @click="generateFdeConfiguration">生成 FDE 方案</button></section><section v-if="fdeConfigurationResult" class="fde-config-result"><h3>客户需求分析</h3><p>{{ fdeConfigurationResult.client_analysis }}</p><h4>系统模块映射</h4><ul><li v-for="item in fdeConfigurationResult.module_mapping" :key="item">{{ item }}</li></ul><h4>实施步骤</h4><ol><li v-for="item in fdeConfigurationResult.implementation_steps" :key="item">{{ item }}</li></ol><h4>验收标准</h4><ul><li v-for="item in fdeConfigurationResult.acceptance_criteria" :key="item">{{ item }}</li></ul><p class="demo-boundary">{{ fdeConfigurationResult.boundary_note }}</p></section><section v-else class="workspace-empty">选择客户类型和需求后，生成一份仅供演练的 FDE 实施方案。</section></div>
      </section>

      <section v-if="activeWorkspaceView === 'fde-config'" class="fde-shortcuts" aria-label="FDE 交付展示入口">
        <span>FDE 交付展示</span><button type="button" @click="openWorkspaceView('fde-mapping')">需求映射</button><button type="button" @click="openWorkspaceView('fde-risks')">实施风险</button><button type="button" @click="openWorkspaceView('fde-delivery-report')">交付报告</button>
      </section>

      <section v-if="activeWorkspaceView === 'fde-diagnosis'" class="fde-config-center enterprise-center" aria-label="FDE Problem Diagnosis">
        <div class="dashboard-heading"><div><p class="section-kicker">FDE PROBLEM DIAGNOSIS · DEMO</p><h2>问题诊断中心</h2><p>将客户反馈转为可沟通的检查项和确认事项，不替代真实故障排查。</p></div></div>
        <div class="diagnosis-input"><textarea v-model="fdeProblemInput" rows="5" placeholder="例如：客户反馈知识库检索不到已上传资料，且输出缺少引用依据。"></textarea><button class="primary-card-action" @click="diagnoseFdeProblem">生成诊断清单</button></div><section v-if="fdeDiagnosisResult" class="diagnosis-result"><article><h3>可能原因</h3><ul><li v-for="item in fdeDiagnosisResult.possible_causes" :key="item">{{ item }}</li></ul></article><article><h3>检查项</h3><ul><li v-for="item in fdeDiagnosisResult.checks" :key="item">{{ item }}</li></ul></article><article><h3>推荐解决方案</h3><ul><li v-for="item in fdeDiagnosisResult.recommendations" :key="item">{{ item }}</li></ul></article><article><h3>需要客户确认</h3><ul><li v-for="item in fdeDiagnosisResult.customer_confirmation" :key="item">{{ item }}</li></ul></article><p class="demo-boundary">{{ fdeDiagnosisResult.boundary_note }}</p></section>
      </section>

      <section v-if="activeWorkspaceView === 'fde-mapping'" class="fde-solution-center enterprise-center" aria-label="Requirement Mapping Center">
        <div class="dashboard-heading"><div><p class="section-kicker">REQUIREMENT MAPPING CENTER · DEMO</p><h2>需求映射中心</h2><p>将客户业务问题映射到解决方案与 ResearchOS 模块，用于 FDE 沟通演练。</p></div></div>
        <div class="fde-scenario-tabs"><button v-for="item in fdeScenarioOptions" :key="item" type="button" :class="{ active: fdeDeliveryScenario === item }" @click="selectFdeDeliveryScenario(item)">{{ item }}</button></div>
        <article class="requirement-map-hero"><span>Demo 场景 · {{ fdeDeliveryScenario }}</span><h3>{{ fdeScenarioProfile.background }}</h3></article>
        <div class="requirement-mapping-flow"><article><span>01 · 客户业务问题</span><p>{{ fdeScenarioProfile.problem }}</p></article><i>↓</i><article><span>02 · 解决方案</span><p>{{ fdeScenarioProfile.solution }}</p></article><i>↓</i><article><span>03 · ResearchOS 模块</span><p>{{ fdeScenarioProfile.mapping[2] }}</p></article></div>
        <p class="demo-boundary">需求映射为 Demo 展示内容；真实客户方案需根据授权资料、现场调研与验收口径确认。</p>
      </section>

      <section v-if="activeWorkspaceView === 'fde-risks'" class="fde-solution-center enterprise-center" aria-label="Implementation Risk Center">
        <div class="dashboard-heading"><div><p class="section-kicker">IMPLEMENTATION RISK CENTER · DEMO</p><h2>实施风险中心</h2><p>在项目启动前明确资料、可信、使用与实施边界，避免将 AI 输出误用为已验证结论。</p></div></div>
        <div class="implementation-risk-grid"><article v-for="risk in implementationRisks" :key="risk.name"><span>DEMO RISK</span><h3>{{ risk.name }}</h3><dl><dt>风险原因</dt><dd>{{ risk.reason }}</dd><dt>可能影响</dt><dd>{{ risk.impact }}</dd><dt>解决建议</dt><dd>{{ risk.recommendation }}</dd></dl></article></div><p class="demo-boundary">风险清单为 FDE 演练模板，不构成对实际客户环境的故障、合规或科研判断。</p>
      </section>

      <section v-if="activeWorkspaceView === 'fde-delivery-report'" class="fde-solution-center enterprise-center" aria-label="FDE Delivery Report">
        <div class="dashboard-heading"><div><p class="section-kicker">FDE DELIVERY REPORT · DEMO</p><h2>客户交付方案报告</h2><p>汇总已有客户场景、方案配置与实施流程，形成可沟通的交付材料。</p></div><button class="primary-card-action" type="button" @click="generateFdeDeliveryReport">生成交付报告</button></div>
        <div v-if="fdeDeliveryReport" class="fde-delivery-report"><header><span>AI辅助生成 · 需要客户确认</span><h3>{{ fdeDeliveryScenario }} · FDE Delivery Report</h3></header><section><h4>客户背景</h4><p>{{ fdeDeliveryReport.customer_background }}</p></section><section><h4>当前问题</h4><p>{{ fdeDeliveryReport.current_problem }}</p></section><section><h4>需求分析</h4><p>{{ fdeDeliveryReport.requirement_analysis }}</p></section><section><h4>系统方案</h4><p>{{ fdeDeliveryReport.system_solution }}</p></section><section><h4>模块映射</h4><ul><li v-for="item in fdeDeliveryReport.module_mapping" :key="item">{{ item }}</li></ul></section><section><h4>实施计划</h4><ol><li v-for="item in fdeDeliveryReport.implementation_plan" :key="item">{{ item }}</li></ol></section><section><h4>验收标准</h4><ul><li v-for="item in fdeDeliveryReport.acceptance_criteria" :key="item">{{ item }}</li></ul></section><footer><b>风险说明</b><p>{{ fdeDeliveryReport.risk_note }}</p></footer></div>
        <div v-else class="workspace-empty">请选择并生成一份 Demo 客户交付方案；报告仅供方案沟通，需客户确认。</div>
      </section>

      <section v-if="activeWorkspaceView === 'fde-demo'" class="fde-demo-center" aria-label="FDE解决方案演示模式">
        <header class="fde-demo-header"><div><p class="section-kicker">FDE SOLUTION DEMO · 5 MINUTES</p><h2>FDE 解决方案演示</h2><p>从客户背景到实施交付的五步说明。以下为 Demo 演练，不调用模型、不生成真实科研结论。</p></div><span>Step {{ fdeDemoStep + 1 }} / 5</span></header>
        <div class="fde-demo-progress"><button v-for="(name,index) in ['客户背景','需求分析','AI解决方案架构','AI执行过程','客户交付']" :key="name" :class="{ active: fdeDemoStep === index, done: fdeDemoStep > index }" @click="fdeDemoStep = index"><b>0{{ index + 1 }}</b>{{ name }}</button></div>
        <section class="fde-demo-content"><template v-if="fdeDemoStep === 0"><p class="section-kicker">CUSTOMER BACKGROUND</p><h3>某低碳建筑材料企业</h3><p>企业希望寻找材料性能优化方向，但实验数据、论文资料和研究成果分散。</p><div class="fde-demo-pain"><article><b>资料分散</b><span>信息整理成本高</span></article><article><b>路线不清</b><span>技术路线探索困难</span></article><article><b>协作断层</b><span>企业需求和实验室能力匹配困难</span></article></div></template><template v-else-if="fdeDemoStep === 1"><p class="section-kicker">FDE REQUIREMENT ANALYSIS</p><h3>需求分析</h3><div class="fde-requirement-map"><article><b>业务需求</b><p>寻找材料优化方案。</p><small>对应：企业需求分析与项目规划</small></article><article><b>系统需求</b><p>建立科研知识空间。</p><small>对应：Research Workspace 与 Knowledge Space</small></article><article><b>AI需求</b><p>辅助资料分析和方案生成。</p><small>对应：Research Worker 与 Human Review</small></article></div></template><template v-else-if="fdeDemoStep === 2"><p class="section-kicker">SOLUTION ARCHITECTURE</p><h3>AI解决方案架构</h3><div class="fde-architecture-flow"><button v-for="name in ['用户需求','Research Master','Research Worker','Tools','RAG知识库','Evidence','Human Review','交付报告']" :key="name" :class="{ active: fdeArchitectureSelection === name }" @click="fdeArchitectureSelection = name">{{ name }}</button></div><aside><b>{{ fdeArchitectureSelection }}</b><p>{{ fdeArchitectureDescriptions[fdeArchitectureSelection] }}</p></aside></template><template v-else-if="fdeDemoStep === 3"><p class="section-kicker">AI EXECUTION · DEMO</p><h3>AI执行过程</h3><div class="fde-execution-demo"><article v-for="item in [['Planning','规划','理解企业任务并拆解资料处理步骤'],['Executing','执行','扫描允许资料并调用既有受控工具'],['Observing','观察','检查资料数量和可验证 Evidence'],['Evaluating','评估','资料不足时明确停止科研结论'],['Delivery','交付','生成待人工审核的说明或报告']]" :key="item[0]"><b>✓</b><div><span>{{ item[0] }}</span><h4>{{ item[1] }}</h4><p>{{ item[2] }}</p></div></article></div><p class="demo-boundary">Demo流程仅展示已有 Research Worker 的用户可读阶段，不代表实际扫描、检索或科研结论。</p></template><template v-else><p class="section-kicker">CLIENT DELIVERY</p><h3>客户交付</h3><div class="fde-delivery-preview"><article><b>客户问题</b><p>资料分散、合作项目准备周期长。</p></article><article><b>解决方案</b><p>Workspace、知识空间、受控执行、Evidence 与人工审核。</p></article><article><b>实施过程</b><p>需求调研 → 配置 → 测试 → 验收。</p></article><article><b>AI能力</b><p>知识检索、资料处理、执行摘要和交付报告。</p></article><article><b>交付成果</b><p>Implementation Acceptance Report 与后续优化建议。</p></article></div><p class="review-result">AI辅助生成 · 需客户确认。真实交付需基于客户授权资料完成验收。</p></template></section>
        <footer class="fde-demo-controls"><button class="outline-button" :disabled="fdeDemoStep === 0" @click="previousFdeDemoStep">上一步</button><button class="primary-card-action" :disabled="fdeDemoStep === 4" @click="nextFdeDemoStep">下一步</button><button v-if="fdeDemoStep === 4" class="primary-card-action" @click="openFdeDeliveryRehearsal">进入FDE交付中心</button></footer>
      </section>

      <section v-if="activeWorkspaceView === 'product-value'" class="value-page enterprise-center" aria-label="产品价值">
        <div class="dashboard-heading"><div><p class="section-kicker">WHY RESEARCHOS</p><h2>为什么客户选择 ResearchOS</h2><p>把资料理解、协作沟通和科研决策辅助组织为可验证的工作流程。</p></div></div><div class="value-role-grid"><article><span>高校实验室</span><h3>科研资料资产化</h3><p>帮助整理科研资料、沉淀可检索知识，并辅助项目管理。</p></article><article><span>企业</span><h3>理解技术方向</h3><p>帮助更快理解可合作的技术方向，辅助产学研沟通与方案准备。</p></article><article><span>高校管理部门</span><h3>科研资源管理</h3><p>帮助查看资料、项目与成果路径，辅助科研资源协调。</p></article></div><p class="demo-boundary">页面说明产品潜在价值，不承诺具体效率、收益、客户数量或科研成功率。</p>
      </section>

      <section v-if="activeWorkspaceView === 'tech-architecture'" class="tech-page enterprise-center" aria-label="技术架构">
        <div class="dashboard-heading"><div><p class="section-kicker">TECHNOLOGY ARCHITECTURE</p><h2>ResearchOS 技术架构</h2><p>以轻量、可解释与受控执行为目标的产品原型架构。</p></div></div><div class="tech-stack-grid"><article><span>Frontend</span><b>Vue 3</b><p>CDN 单页工作空间</p></article><article><span>Backend</span><b>FastAPI</b><p>REST API 与业务服务</p></article><article><span>AI</span><b>Multi-Agent</b><p>Research Master 协同现有专项能力</p></article><article><span>Knowledge</span><b>RAG + FAISS</b><p>基于授权上传资料检索</p></article><article><span>Trust</span><b>Evidence + Human Review</b><p>章节级资料提示与人工确认</p></article><article><span>Execution</span><b>Research Worker</b><p>受控工具与可读执行摘要</p></article></div>
      </section>

      <section v-if="activeWorkspaceView === 'fde-delivery'" class="fde-delivery-center" aria-label="FDE交付中心">
        <header class="dashboard-heading"><div><p class="section-kicker">FDE DELIVERY PIPELINE · DEMO</p><h2>FDE 交付中心</h2><p>低碳建筑材料企业与高校实验室的实施演练。所有内容均为 Demo 流程，不代表真实客户实施结果。</p></div><button class="primary-card-action" @click="advanceFdeStage">推进当前阶段</button></header>
        <div class="fde-delivery-grid"><aside class="fde-stage-list"><button v-for="(stage, index) in ['需求调研','方案设计','系统配置','测试验证','上线交付']" :key="stage" type="button" :class="{ active: fdeStageIndex === index, done: fdeStageIndex > index }" @click="fdeStageIndex = index"><b>0{{ index + 1 }}</b><span>{{ stage }}</span></button></aside>
          <section class="fde-stage-detail"><p class="section-kicker">STAGE {{ fdeStageIndex + 1 }}</p><template v-if="fdeStageIndex === 0"><h3>需求调研</h3><dl><dt>客户目标</dt><dd>提升低碳建筑材料性能，并缩短企业合作项目准备周期。</dd><dt>业务痛点</dt><dd>实验室资料分散，知识传递与项目准备依赖人工整理。</dd><dt>现有资料</dt><dd>Demo 环境不将演示资料写入知识库；真实实施需由客户授权上传资料。</dd></dl></template><template v-else-if="fdeStageIndex === 1"><h3>方案设计</h3><dl><dt>Agent方案</dt><dd>Research Master 负责决策辅助，Research Worker 负责受控资料处理。</dd><dt>数据方案</dt><dd>使用现有 SQLite、文件工作区与受控数据工具。</dd><dt>知识库方案</dt><dd>仅以客户授权并完成索引的资料进入既有 RAG/FAISS 流程。</dd></dl></template><template v-else-if="fdeStageIndex === 2"><h3>系统配置</h3><dl><dt>Workspace创建</dt><dd>建立客户独立 Research Workspace，并展示成员角色。</dd><dt>资料上传</dt><dd>通过既有论文库或科研工作区接收可读取资料。</dd><dt>Agent配置</dt><dd>沿用现有受控工具与 Evidence/Human Review 边界。</dd></dl></template><template v-else-if="fdeStageIndex === 3"><h3>测试验证</h3><dl><dt>任务执行</dt><dd>运行文献、数据或企业需求任务。</dd><dt>Evidence检查</dt><dd>没有可验证资料时，系统只能生成资料不足说明。</dd><dt>人工审核</dt><dd>负责人审核 AI 建议后，才可进入现有 Action/Decision 流程。</dd></dl></template><template v-else><h3>上线交付</h3><dl><dt>报告交付</dt><dd>提供 AI 辅助生成、需人工审核的实施与客户交付报告。</dd><dt>培训说明</dt><dd>说明资料上传、Evidence 验证、人工确认和限制边界。</dd><dt>后续优化</dt><dd>根据客户真实资料覆盖与验收反馈迭代，不承诺未验证科研结果。</dd></dl></template></section>
          <aside class="fde-value-panel"><p class="section-kicker">CUSTOMER VALUE</p><h3>客户需求分析</h3><p>“实验室资料分散，企业合作项目准备周期长。”</p><div class="fde-tag-list"><span>数据管理</span><span>AI分析</span><span>项目协作</span><span>成果管理</span></div><h4>关联 ResearchOS 模块</h4><ul><li>Research Workspace</li><li>知识空间与 RAG</li><li>Research Worker</li><li>Evidence + Human Review</li></ul></aside></div>
        <section class="fde-implementation"><div><p class="section-kicker">IMPLEMENTATION TASKS</p><h3>实施任务列表</h3></div><article v-for="(name,index) in ['收集客户资料','建立知识空间','配置Agent流程','测试任务效果','客户验收']" :key="name"><b>0{{ index + 1 }}</b><span>{{ name }}</span><em :class="fdeTaskStatuses[index]">{{ fdeTaskStatuses[index] }}</em></article></section>
        <section class="fde-acceptance"><div><p class="section-kicker">IMPLEMENTATION ACCEPTANCE REPORT</p><h3>实施验收报告</h3><span>AI辅助生成 · 需客户确认</span></div><dl><dt>客户需求</dt><dd>资料管理、AI分析、项目协作和成果规划。</dd><dt>实施内容</dt><dd>Research Workspace、任务中心、受控 Worker、Evidence 与人工审核流程。</dd><dt>系统能力</dt><dd>资料理解、知识检索、交付报告与可追溯执行摘要。</dd><dt>测试结果</dt><dd>Demo 流程可完整展示；真实科研结论需使用客户授权资料另行验收。</dd><dt>限制说明</dt><dd>非生产系统；不包含登录、多租户隔离或生产级持久化。</dd><dt>后续建议</dt><dd>以真实资料覆盖、客户验收反馈和权限体系作为下一阶段实施输入。</dd></dl><p v-if="fdeAcceptanceReady" class="review-result">交付阶段已推进至上线交付。请由客户负责人确认本演练报告。</p></section>
      </section>

      <section v-if="activeWorkspaceView === 'autonomous'" class="autonomous-workspace" aria-label="自主科研执行工作空间">
        <div class="dashboard-heading"><div><p class="section-kicker">AI RESEARCH WORKER</p><h2>AI Research Workspace</h2><p>Research Brain 先感知真实科研环境，再规划、执行、观察和评估；只有具备可追溯资料依据时才形成待人工确认的交付物。</p></div></div>
        <p v-if="autonomousError" class="error-alert"><span>!</span>{{ autonomousError }}</p>
        <div class="autonomous-grid"><section class="task-config-card"><label for="autonomous-goal">当前科研目标</label><textarea id="autonomous-goal" v-model="autonomousGoal" rows="7" placeholder="例如：帮助低碳建筑材料实验室寻找企业合作创新方向。"></textarea><p class="tool-boundary">Research Worker 仅读取 <code>research_workspace/</code> 中允许的科研文件，并调用现有知识库；不会控制电脑、执行 Shell 命令或自动创建项目。</p><button class="analyze-button" type="button" :disabled="autonomousLoading" @click="runAutonomousResearch"><span v-if="autonomousLoading" class="spinner small-spinner"></span>{{ autonomousLoading ? 'AI Research Worker 正在执行…' : '启动 AI Research Worker' }}</button><details class="compact-details"><summary>可调用工具（{{ autonomousTools.length }}）</summary><ul class="tool-catalog"><li v-for="tool in autonomousTools" :key="tool.id"><b>{{ tool.name }}</b><span>{{ tool.description }}</span></li></ul></details></section>
          <section class="autonomous-result-card"><div v-if="autonomousLoading" class="loading-state"><span class="spinner"></span><h3>AI Research Worker 正在执行受控任务</h3><ol class="loading-workflow"><li><i></i>感知科研环境并理解目标</li><li><i></i>规划任务并选择工具</li><li><i></i>观察结果、检查证据</li><li><i></i>反思并生成待复核交付物</li></ol></div><div v-else-if="!autonomousRun" class="empty-state"><div class="empty-illustration">◌</div><h3>等待科研目标</h3><p>先上传并索引资料，或在 <code>research_workspace/</code> 放入允许的科研文件。</p></div><div v-else class="autonomous-result"><p class="section-kicker">RUN · {{ autonomousRun.status }}</p><h3>{{ autonomousRun.goal }}</h3><div class="autonomous-status-grid"><article><span>当前步骤</span><b>{{ autonomousRun.current_step || '等待执行' }}</b></article><article><span>当前工具</span><b>{{ autonomousRun.current_tool || '尚未调用' }}</b></article><article><span>已完成任务</span><b>{{ (autonomousRun.completed_tasks || []).length }}</b></article></div><details open class="master-plan-card"><summary>AI 已理解的科研环境</summary><p>资料：{{ autonomousRun.environment_profile?.documents || 0 }} 个 · 论文：{{ autonomousRun.environment_profile?.papers || 0 }} 篇 · 数据集：{{ autonomousRun.environment_profile?.datasets || 0 }} 个</p><p v-if="(autonomousRun.environment_profile?.research_topics || []).length">文件名线索：{{ autonomousRun.environment_profile.research_topics.join('、') }}</p><p class="trace-boundary">{{ autonomousRun.environment_profile?.boundary_note }}</p></details><details class="master-plan-card"><summary>实验室长期记忆</summary><p>已上传论文：{{ autonomousRun.memory_snapshot?.knowledge_assets?.papers || 0 }} 篇 · 已就绪：{{ autonomousRun.memory_snapshot?.knowledge_assets?.ready_papers || 0 }} 篇 · 历史任务：{{ autonomousRun.memory_snapshot?.organization_context?.historical_agent_runs || 0 }}</p><p v-if="(autonomousRun.memory_snapshot?.research_directions || []).length">标题线索：{{ autonomousRun.memory_snapshot.research_directions.join('、') }}</p><p class="trace-boundary">{{ autonomousRun.memory_snapshot?.memory_boundary }}</p></details><section class="agent-run-board"><h4>任务计划与工具选择</h4><article v-for="item in autonomousRun.task_plan?.tasks || []" :key="item.id"><b>{{ item.status === 'completed' ? '✓' : '•' }}</b><div><strong>{{ item.task }}</strong><p>{{ item.agent }} · {{ item.tool }}<br><small>选择原因：{{ item.tool_selection_reason || '根据当前任务计划执行。' }}</small></p></div><span>{{ item.status }}</span></article></section><section class="agent-run-board"><h4>用户可读执行时间线</h4><article v-for="(item, index) in autonomousRun.execution_timeline || []" :key="index"><b>{{ index + 1 }}</b><div><strong>{{ item.actor }}</strong><p>{{ item.message }}</p></div><span>{{ item.status }}</span></article></section><details open class="master-plan-card"><summary>结果检查、反思与下一步</summary><p>{{ autonomousRun.reflection?.next_decision || '暂无下一步建议。' }}</p><ul><li v-for="item in autonomousRun.next_plan || []" :key="item.action">{{ item.action }}：{{ item.reason }}</li></ul><p class="trace-boundary">{{ autonomousRun.reflection?.boundary_note }}</p><p>证据数量：{{ autonomousRun.reflection?.evidence_count || 0 }} · 目标覆盖：{{ autonomousRun.reflection?.goal_coverage ? '满足' : '待补充' }}</p></details><details v-if="autonomousRun.final_output?.research_result?.executive_summary" open class="master-plan-card"><summary>最终科研交付物（待人工确认）</summary><p>{{ autonomousRun.final_output.research_result.executive_summary }}</p></details><details class="master-plan-card"><summary>证据依据（{{ (autonomousRun.final_output?.evidence || []).length }}）</summary><p v-if="!(autonomousRun.final_output?.evidence || []).length">暂无可验证资料。</p><article v-for="source in autonomousRun.final_output?.evidence || []" :key="source.paper_id + source.section"><b>{{ source.source }}</b><span>{{ source.section }} · {{ source.score }}</span></article></details></div></section></div>
        <section v-if="autonomousRuns.length" class="autonomous-history"><h3>最近执行记录</h3><button v-for="item in autonomousRuns" :key="item.id" type="button" @click="autonomousRun = item"><span>{{ item.status }}</span><b>{{ item.goal }}</b><small>{{ formatLibraryDate(item.updated_at) }}</small></button></section>
      </section>

      <section v-if="activeWorkspaceView === 'projects'" class="researchos-projects" aria-label="科研项目中心"><div class="dashboard-heading"><div><p class="section-kicker">RESEARCH PROJECT LIFECYCLE</p><h2>科研项目中心</h2><p>把企业需求、研究目标、技术路线、论文专利规划和成果管理放在同一条项目生命周期中。</p></div></div><p v-if="projectError" class="error-alert"><span>!</span>{{ projectError }}</p><div class="project-workspace"><section class="task-config-card"><label>新建科研项目</label><input v-model="projectForm.name" placeholder="项目名称，例如：低碳建筑材料关键技术研发" /><textarea v-model="projectForm.enterprise_requirement" rows="4" placeholder="企业需求：例如开发绿色建筑材料并验证工程适用性"></textarea><textarea v-model="projectForm.research_goal" rows="3" placeholder="研究目标"></textarea><textarea v-model="projectForm.technology_route" rows="3" placeholder="技术路线（可后续完善）"></textarea><textarea v-model="projectForm.paper_plan" rows="2" placeholder="论文规划"></textarea><textarea v-model="projectForm.patent_plan" rows="2" placeholder="专利规划"></textarea><textarea v-model="projectForm.outcome_management" rows="2" placeholder="成果管理"></textarea><button class="analyze-button" type="button" :disabled="projectLoading" @click="createResearchProject">{{ projectLoading ? '保存中…' : '创建科研项目' }}</button></section><section class="project-list-panel"><div v-if="projectLoading && !researchProjects.length" class="loading-state"><span class="spinner"></span><p>正在读取项目…</p></div><div v-else-if="!researchProjects.length" class="empty-state"><div class="empty-illustration">◫</div><h3>暂无科研项目</h3><p>创建项目后，可用 Project Agent 评估企业需求与实验室能力匹配。</p></div><article v-for="project in researchProjects" :key="project.id" class="project-card"><div><span>{{ project.status }}</span><time>{{ formatLibraryDate(project.updated_at) }}</time></div><h3>{{ project.name }}</h3><p>{{ project.research_goal || project.enterprise_requirement || '尚未补充项目目标。' }}</p><footer><span>论文：{{ project.paper_plan ? '已规划' : '待规划' }} · 专利：{{ project.patent_plan ? '已规划' : '待规划' }}</span><button class="primary-card-action" type="button" :disabled="projectMatching" @click="runProjectMatch(project)">{{ projectMatching ? '匹配中…' : '需求匹配' }}</button></footer></article></section></div><section v-if="projectMatchResult" class="project-match-result"><p class="section-kicker">PROJECT AGENT RESULT</p><h3>{{ projectMatchResult.projectName }} · 横向需求匹配</h3><div class="project-match-grid"><article><h4>实验室能力匹配</h4><ul><li v-for="item in projectMatchResult.lab_capability_match" :key="item">{{ item }}</li></ul></article><article><h4>技术方案建议</h4><ul><li v-for="item in projectMatchResult.technical_solution_suggestions" :key="item">{{ item }}</li></ul></article><article><h4>预期成果规划</h4><dl><template v-for="(value,key) in projectMatchResult.expected_outcome_plan" :key="key"><dt>{{ key }}</dt><dd>{{ Array.isArray(value) ? value.join('、') : value }}</dd></template></dl></article><article><h4>风险与待确认问题</h4><ul><li v-for="item in projectMatchResult.risks_and_questions" :key="item">{{ item }}</li></ul></article></div><section class="agent-run-board"><h4>Project Agent 执行过程</h4><article v-for="trace in projectMatchResult.agent_trace" :key="trace.agent"><b>✓</b><div><strong>{{ trace.agent }}</strong><p>{{ trace.message }}</p></div><span>已完成</span></article></section><p class="trace-boundary">{{ projectMatchResult.boundary_note }}</p></section></section>

      <section v-if="activeWorkspaceView === 'bi'" class="researchos-bi" aria-label="科研BI驾驶舱"><div class="dashboard-heading"><div><p class="section-kicker">RESEARCH BUSINESS INTELLIGENCE</p><h2>科研 BI 驾驶舱</h2><p>从团队已沉淀资料中查看科研资产、成果统计与技术路线状态。</p></div><button class="outline-button" type="button" :disabled="researchBiLoading" @click="loadResearchBi">{{ researchBiLoading ? '刷新中…' : '刷新数据' }}</button></div><p v-if="projectError" class="error-alert"><span>!</span>{{ projectError }}</p><div v-if="researchBi" class="bi-grid"><article><p>科研论文 / 资料</p><strong>{{ researchBi.research_assets?.papers || 0 }}</strong><span>已入库科研资产</span></article><article><p>知识片段</p><strong>{{ researchBi.research_assets?.knowledge_chunks || 0 }}</strong><span>可用于 Agent 检索</span></article><article><p>科研项目</p><strong>{{ researchBi.research_assets?.projects || 0 }}</strong><span>生命周期管理中</span></article></div><div v-if="researchBi" class="researchos-dashboard-grid"><section class="dashboard-card"><p class="section-kicker">ASSET DISTRIBUTION</p><h3>科研资料构成</h3><ul class="bi-list"><li v-for="item in researchBi.asset_distribution" :key="item.document_type"><span>{{ item.document_type }}</span><b>{{ item.count }}</b></li></ul><p v-if="!researchBi.asset_distribution?.length">暂无已入库资料。</p></section><section class="dashboard-card"><p class="section-kicker">TECHNOLOGY ROADMAP</p><h3>技术路线图</h3><ol class="researchos-flow"><li v-for="item in researchBi.technology_roadmap" :key="item">{{ item }}</li></ol></section><section class="dashboard-card"><p class="section-kicker">RESEARCH HOTSPOTS</p><h3>研究热点分析</h3><p>{{ researchBi.trend_boundary }}</p><ul class="bi-list"><li v-for="title in researchBi.latest_assets" :key="title"><span>{{ title }}</span></li></ul><button class="outline-button" type="button" @click="openWorkspaceView('tasks')">运行趋势分析任务</button></section></div></section>

      <section v-if="activeWorkspaceView === 'agents'" class="researchos-agents ai-team-room" aria-label="AI Worker Capabilities"><div class="dashboard-heading"><div><p class="section-kicker">AI WORKER</p><h2>One worker. Four controlled skills.</h2><p>AI Worker uses approved capabilities, keeps Evidence traceable, and pauses when a human decision is required.</p></div><button class="outline-button" type="button" @click="openWorkspaceView('mission-center')">Open workflow</button></div><div v-if="aiWorkerSkills.length" class="ai-team-roster"><article v-for="skill in aiWorkerSkills" :key="skill.id"><div class="team-presence"><span>{{ skill.name.slice(0, 1) }}</span><i></i></div><div class="team-profile"><p>AI Worker</p><h3>{{ skill.name }}</h3><small>{{ skill.description }}</small></div><div class="team-capability"><span>{{ skill.approval_required ? 'REVIEW GATED' : 'READY' }}</span><b>{{ skill.evidence_required ? 'Traceable Evidence required' : 'Controlled execution boundary' }}</b><em>{{ skill.approval_required ? 'Human approval' : 'Evidence-aware' }}</em></div></article></div><div v-else class="product-empty-state"><b>AI Worker capability catalog unavailable</b><p>Reconnect the workspace to load the currently approved capabilities.</p><button class="primary-card-action" type="button" @click="openWorkspaceView('agents')">Reconnect</button></div></section>

      <section v-if="activeWorkspaceView === 'knowledge'" class="library-workspace" aria-label="Knowledge Space">
        <div class="library-header"><div><p class="section-kicker">RESEARCH KNOWLEDGE SPACE</p><h2>Knowledge Space</h2><p>科研资料在这里成为可检索、可引用、可用于持续研究的知识资产。</p></div><div class="library-header-actions"><select v-model="libraryDocumentType" aria-label="科研资料类型"><option value="paper">论文</option><option value="patent">专利</option><option value="experiment_report">实验报告</option><option value="project_material">项目资料</option></select><label class="library-upload-button" :class="{ busy: libraryUploading }"><input ref="libraryFileInput" type="file" accept="application/pdf,.pdf" :disabled="libraryUploading" @change="uploadLibraryPaper" /><span>{{ libraryUploading ? '正在保存资料…' : '＋ 上传 PDF 资料' }}</span></label><button class="outline-button" type="button" :disabled="libraryLoading" @click="loadLibraryPapers">{{ libraryLoading ? '刷新中' : '刷新列表' }}</button></div></div>
        <div v-if="libraryPapers.length" class="library-toolbar"><label><span>⌕</span><input v-model="librarySearch" type="search" placeholder="Search your research knowledge" /></label><select v-model="libraryStatusFilter" aria-label="按知识库状态筛选"><option value="all">全部状态</option><option value="ready">Ready</option><option value="indexed">Indexed</option><option value="parsed">Parsed</option><option value="failed">Failed</option></select><small>{{ filteredLibraryPapers.length }} / {{ libraryPapers.length }} knowledge assets</small></div>
        <p v-if="libraryError" class="error-alert" role="alert"><span>!</span>{{ libraryError }}</p>
        <div v-if="libraryLoading && !libraryPapers.length" class="library-empty-state"><span class="spinner"></span><p>正在加载论文库…</p></div>
        <div v-else-if="!libraryPapers.length" class="library-empty-state"><div class="empty-illustration">▣</div><h3>暂无科研资料，上传第一篇论文开始分析</h3><p>上传可提取文本的 PDF 后，它会成为科研知识空间中的一份资料。</p></div>
        <div v-else-if="!filteredLibraryPapers.length" class="library-empty-state"><div class="empty-illustration">⌕</div><h3>没有匹配的科研资料</h3><p>试试调整关键词或知识库状态筛选条件。</p></div>
        <div v-else class="library-layout"><div class="paper-card-list"><article v-for="paper in filteredLibraryPapers" :key="paper.paper_id" class="paper-library-card knowledge-asset-card" :class="{ selected: selectedLibraryPaper?.paper_id === paper.paper_id }"><div class="paper-card-top"><span class="paper-status">{{ paper.quality_status || libraryStatusLabel(paper.analysis_status) }}</span><details class="paper-more"><summary aria-label="更多操作">•••</summary><button type="button" @click="deleteLibraryPaper(paper)">删除资料</button></details></div><h3>{{ paper.title }}</h3><p class="paper-filename">{{ documentTypeLabel(paper.document_type) }} · {{ paper.filename }}</p><div class="knowledge-summary"><span>AI 就绪说明</span><p>{{ knowledgeAssetSummary(paper) }}</p></div><div class="knowledge-tags"><span v-for="agent in knowledgeAssetAgents(paper)" :key="agent">{{ agent }}</span><span>{{ paper.chunk_count ?? 0 }} 个知识片段</span></div><div class="paper-card-actions"><button type="button" class="primary-card-action" :disabled="libraryAnalysisLoading" @click="analyzeLibraryPaper(paper)">{{ libraryAnalysisLoading && selectedLibraryPaper?.paper_id === paper.paper_id ? '分析中…' : '进入分析' }}</button><button type="button" class="text-button" @click="viewLibraryPaper(paper)">查看资料</button></div></article></div><aside v-if="libraryPaperDetail" class="library-detail-panel"><div class="library-detail-heading"><div><p class="section-kicker">KNOWLEDGE ASSET DETAIL</p><h3>{{ libraryPaperDetail.title }}</h3></div><button type="button" class="text-button" @click="libraryPaperDetail = null">关闭</button></div><dl><div><dt>资料类型</dt><dd>{{ documentTypeLabel(libraryPaperDetail.document_type) }}</dd></div><div><dt>文件名</dt><dd>{{ libraryPaperDetail.filename }}</dd></div><div><dt>知识库状态</dt><dd>{{ libraryPaperDetail.quality_status || libraryStatusLabel(libraryPaperDetail.analysis_status) }}</dd></div><div><dt>知识片段</dt><dd>{{ libraryPaperDetail.chunk_count ?? 0 }} 个</dd></div><div><dt>更新时间</dt><dd>{{ formatLibraryDate(libraryPaperDetail.updated_at || libraryPaperDetail.upload_time) }}</dd></div><div><dt>文本长度</dt><dd>{{ formatTextLength(libraryPaperDetail.text_length) }}</dd></div></dl><button type="button" class="analyze-button" :disabled="libraryAnalysisLoading" @click="analyzeLibraryPaper(libraryPaperDetail)">{{ libraryAnalysisLoading ? '正在进入 AI助手分析…' : '进入 AI 分析' }}</button></aside></div>
      </section>

      <section v-if="activeWorkspaceView === 'outcomes'" class="research-reports" aria-label="成果规划">
        <div class="library-header"><div><p class="section-kicker">OUTCOME PLANNING</p><h2>成果规划</h2><p>这里保留从知识资产生成的历史分析成果；查看后会回到原有 AI 助手结果区。</p></div><div class="library-header-actions"><button class="outline-button" type="button" :disabled="reportsLoading" @click="loadResearchReports">{{ reportsLoading ? '刷新中' : '刷新报告' }}</button></div></div>
        <p v-if="reportsError" class="error-alert" role="alert"><span>!</span>{{ reportsError }}</p>
        <div v-if="reportsLoading && !reportRecords.length" class="library-empty-state"><span class="spinner"></span><p>正在读取研究报告…</p></div>
        <div v-else-if="!reportRecords.length" class="library-empty-state"><div class="empty-illustration">▤</div><h3>暂无历史研究报告</h3><p>从“我的论文库”进入 AI 分析后，报告会自动保存在这里。</p></div>
        <div v-else class="report-record-list"><article v-for="report in reportRecords" :key="report.id" class="report-record-card" :class="{ selected: selectedReport?.id === report.id }"><div><span class="paper-status">{{ report.scenario }}</span><time>{{ formatLibraryDate(report.created_at) }}</time></div><h3>{{ report.paper_title }}</h3><p>{{ report.task }}</p><footer><span>{{ report.role }}</span><button type="button" class="primary-card-action" :disabled="reportDetailLoading" @click="viewResearchReport(report)">{{ reportDetailLoading && selectedReport?.id === report.id ? '正在恢复…' : '查看报告' }}</button></footer></article></div>
      </section>

      <section v-if="activeWorkspaceView === 'insights'" class="rag-workspace" aria-label="科研洞察">
        <div class="library-header"><div><p class="section-kicker">RESEARCH INSIGHTS</p><h2>科研洞察</h2><p>AI Worker 的 Research Skill 会检索团队知识库中的相关片段，再基于引用证据回答问题。</p></div><div class="library-header-actions"><button class="outline-button" type="button" :disabled="libraryLoading" @click="loadLibraryPapers">{{ libraryLoading ? '刷新中' : '刷新论文范围' }}</button></div></div>
        <p v-if="ragError" class="error-alert" role="alert"><span>!</span>{{ ragError }}</p>
        <div v-if="!libraryPapers.length && !libraryLoading" class="library-empty-state"><div class="empty-illustration">⌕</div><h3>暂无可检索论文</h3><p>请先在“我的论文库”上传论文，并等待知识索引建立完成。</p></div>
        <div v-else class="rag-content"><section class="knowledge-status-strip" aria-label="当前知识库状态"><div><span>论文</span><strong>{{ libraryPapers.length }}</strong><small>篇资料</small></div><div><span>知识片段</span><strong>{{ knowledgeChunkTotal }}</strong><small>个可检索片段</small></div><div><span>已就绪</span><strong>{{ readyPaperCount }}</strong><small>篇论文</small></div></section><details class="rag-scope compact-details"><summary>选择论文范围</summary><div class="rag-paper-options"><label v-for="paper in libraryPapers" :key="paper.paper_id"><input v-model="ragSelectedPaperIds" type="checkbox" :value="paper.paper_id" :disabled="!['indexed', 'ready'].includes(paper.quality_status || paper.analysis_status)" /><span>{{ paper.title }}</span><em>{{ paper.quality_status || libraryStatusLabel(paper.analysis_status) }}</em></label></div></details>
          <section class="research-task-center"><div><p class="section-kicker">RESEARCH TASK CENTER</p><h3>研究任务中心</h3><p>选择任务后，Agent 会检索选定论文并生成结构化研究报告。</p></div><div class="report-task-options"><button v-for="item in ragReportTasks" :key="item.id" type="button" :class="{ active: ragReportType === item.id }" @click="ragReportType = item.id"><b>{{ item.name }}</b><small>{{ item.description }}</small></button></div><button class="outline-button" type="button" :disabled="ragReportLoading" @click="generateResearchReport">{{ ragReportLoading ? '正在生成研究报告…' : '生成结构化报告' }}</button><p v-if="ragReportError" class="error-alert" role="alert"><span>!</span>{{ ragReportError }}</p><div v-if="ragReportResult" class="rag-report-card"><div class="rag-answer-heading"><div><p class="section-kicker">STRUCTURED RESEARCH REPORT</p><h3>研究任务结果</h3></div><span>{{ ragReportQuality?.evidence_level || 'low' }} evidence</span></div><article v-for="(value, key) in ragReportResult" :key="key"><h4>{{ key }}</h4><p v-if="typeof value === 'string'">{{ value }}</p><ul v-else><li v-for="item in value" :key="item">{{ item }}</li></ul></article><footer v-if="ragReportEvaluation">检索质量：<b>{{ ragReportEvaluation.retrieval_quality }}</b> · {{ ragReportEvaluation.retrieval_count }} 条证据 · 最高分 {{ ragReportEvaluation.highest_score }}</footer></div></section>
          <div class="rag-question-form"><label for="rag-question">请输入科研知识问题</label><textarea id="rag-question" v-model="ragQuestion" rows="5" placeholder="例如：总结这些论文在研究方法上的差异，并说明各自的适用边界。"></textarea><button class="analyze-button" type="button" :disabled="ragLoading || !libraryPapers.length" @click="askResearchQuestion"><span v-if="ragLoading" class="spinner small-spinner"></span>{{ ragLoading ? 'Agent 正在检索论文证据…' : '开始知识问答' }}</button></div>
          <div v-if="ragLoading" class="loading-state rag-loading"><div class="process-heading"><span class="spinner"></span><div><h3>AI Worker 正在处理问题</h3><p>Research Skill 正在分析问题、改写检索 Query、检索相关论文、筛选证据并生成回答。</p></div></div><ol class="loading-workflow"><li><i></i>分析研究任务</li><li><i></i>检索相关论文</li><li><i></i>筛选与重排证据</li><li><i></i>生成可信回答</li></ol></div>
          <details v-if="ragAgentPlan && !ragLoading" class="rag-plan compact-details"><summary>AI 执行过程</summary><span>✓ 理解问题</span><span>✓ 检索论文</span><span>✓ 筛选证据</span><span>✓ 生成回答</span><p>{{ ragAgentPlan.instruction }}</p><small>优化检索 Query：{{ ragAgentPlan.retrieval_query }}</small></details>
          <details v-if="ragAgentTrace?.steps?.length" class="rag-trace compact-details" aria-label="AI执行过程"><summary>查看执行摘要</summary><ol><li v-for="(trace, index) in ragAgentTrace.steps" :key="trace.created_at + trace.step"><b>✓</b><div><strong>{{ index + 1 }}. {{ trace.step }}</strong><p>{{ trace.message }}</p></div></li></ol></details>
          <details v-if="ragRetrievalEvaluation" class="rag-evaluation compact-details" aria-label="检索效果"><summary>检索质量 · {{ ragRetrievalEvaluation.retrieval_quality }}</summary><dl><div><dt>检索证据</dt><dd>{{ ragRetrievalEvaluation.retrieval_count }} 条</dd></div><div><dt>平均分</dt><dd>{{ ragRetrievalEvaluation.average_score }}</dd></div><div><dt>最高分</dt><dd>{{ ragRetrievalEvaluation.highest_score }}</dd></div></dl><small>该评分反映检索匹配质量，不代表回答事实准确率。</small></details>
          <details v-if="ragConflictReport" class="rag-conflict-check compact-details" :class="ragConflictReport.status"><summary>Conflict Check · {{ ({ no_conflict: '未发现明显冲突', potential_conflict: '发现潜在差异', context_difference: '研究条件不同', insufficient_evidence: '可比较资料不足' })[ragConflictReport.status] || '待检查' }}</summary><p>{{ ragConflictReport.reason }}</p><small>检测方式：{{ ragConflictReport.detection_method || 'rule_based_initial_detection' }}。未发现明显冲突不代表所有研究结论一致。</small><article v-for="(item, index) in ragConflictReport.conflicts || []" :key="index"><b>{{ item.topic || '相近研究主题' }}</b><p>{{ item.position_a }}</p><p>{{ item.position_b }}</p><p>条件说明：{{ item.context_difference || '未识别到足够条件信息。' }}</p><p>建议：核验研究对象、实验条件与样本定义，并由科研负责人复核。</p><div><span v-for="ref in item.evidence_refs || []" :key="ref.evidence_id">{{ ref.source }} · {{ ref.section }}</span></div></article></details>
          <div v-if="ragAnswer" class="rag-answer-card"><div class="rag-answer-heading"><div><p class="section-kicker">EVIDENCE-GROUNDED ANSWER</p><h3>AI 回答</h3></div><span>检索匹配度：{{ ragConfidence }}</span></div><p>{{ ragAnswer }}</p><footer v-if="ragSourceQuality">证据等级：<b>{{ ragSourceQuality.evidence_level }}</b> · {{ ragSourceQuality.citation_count }} 条引用 · 平均分 {{ ragSourceQuality.average_score }}</footer></div>
          <div v-if="ragSources.length" class="rag-sources"><div class="result-section-heading"><div><p class="section-kicker">RETRIEVAL SOURCES</p><h3>引用论文片段</h3></div><span>{{ ragSources.length }} 条证据</span></div><article v-for="(source, index) in ragSources" :key="source.paper_id + '-' + index" class="rag-source-card" tabindex="0" @click="showRagSource(source)"><div><span class="evidence-number">{{ index + 1 }}</span><div><h4>{{ source.paper_title }}</h4><p>章节：{{ source.section }}</p></div><strong>{{ Number(source.score).toFixed(4) }}</strong></div><blockquote>{{ source.content }}</blockquote></article></div>
          <aside v-if="ragSelectedSource" class="rag-source-detail"><div class="library-detail-heading"><div><p class="section-kicker">SOURCE DETAIL</p><h3>{{ ragSelectedSource.paper_title }}</h3></div><button type="button" class="text-button" @click="ragSelectedSource = null">关闭</button></div><p><b>来源章节：</b>{{ ragSelectedSource.section }}</p><blockquote>{{ ragSelectedSource.content }}</blockquote><small>相似度：{{ Number(ragSelectedSource.score).toFixed(4) }}</small></aside>
          <section class="rag-history"><div class="result-section-heading"><div><p class="section-kicker">RAG HISTORY</p><h3>历史知识问答</h3></div><button class="text-button" type="button" @click="loadRagHistory">{{ ragHistoryLoading ? '加载中' : '刷新' }}</button></div><p v-if="!ragHistory.length" class="field-hint">暂无历史知识问答。</p><article v-for="record in ragHistory" :key="record.id"><div><b>{{ record.question }}</b><time>{{ formatLibraryDate(record.created_at) }}</time></div><p>{{ record.answer }}</p><button type="button" class="text-button" @click="restoreRagHistory(record)">查看引用</button></article></section>
        </div>
      </section>

      <section v-if="activeWorkspaceView === 'tasks' && researchOsTaskResult" class="value-agent-card task-value-entry"><div><p class="section-kicker">VALUE AGENT</p><h3>科研价值评估</h3><p>对当前研究方向的资料覆盖、创新机会和成果路径进行辅助判断。</p></div><button class="outline-button" type="button" :disabled="valueAssessmentLoading" @click="assessResearchValue">{{ valueAssessmentLoading ? '评估中…' : '运行 Value Agent' }}</button><div v-if="valueAssessment" class="value-agent-grid"><article v-for="item in [['研究热度',valueAssessment.research_heat],['创新潜力',valueAssessment.innovation_potential],['成果潜力',valueAssessment.outcome_potential]]" :key="item[0]"><h4>{{ item[0] }} <span :class="item[1].level">{{ item[1].level }}</span></h4><p>{{ item[1].explanation }}</p></article></div><p v-if="valueAssessment" class="trace-boundary">{{ valueAssessment.boundary_note }}</p></section>

      <section v-if="activeWorkspaceView === 'bi' && researchBi" class="bi-visual-board"><section><p class="section-kicker">RESEARCH HOTSPOT TREND</p><h3>热点趋势图</h3><div class="bar-chart"><div v-for="item in researchBi.asset_distribution" :key="item.document_type"><span :style="{ height: Math.max(12, item.count * 24) + 'px' }"></span><small>{{ item.document_type }}</small></div></div><p>柱状高度表示当前已入库资料类型数量，不代表外部领域热度。</p></section><section><p class="section-kicker">OUTCOME CONVERSION</p><h3>成果转化漏斗</h3><ol class="funnel-list"><li v-for="item in researchBi.outcome_funnel" :key="item.stage"><span>{{ item.stage }}</span><b>{{ item.count }}</b></li></ol></section><section><p class="section-kicker">LAB CAPABILITY</p><h3>科研能力雷达</h3><div class="radar-list"><div v-for="item in researchBi.capability_radar" :key="item.name"><span>{{ item.name }}</span><i><b :style="{ width: item.score + '%' }"></b></i><em>{{ item.score }}</em></div></div><p>评分反映本地资料、项目与成果规划覆盖度，不代表实验室真实能力评级。</p></section></section>

      <section v-if="activeWorkspaceView === 'fde-report'" class="fde-report" aria-label="FDE解决方案报告"><div class="dashboard-heading"><div><p class="section-kicker">FDE SOLUTION DELIVERY</p><h2>FDE 解决方案报告</h2><p>将客户需求、实验室知识资产与 Agent 输出整合为一份可沟通的科研合作交付物。</p></div><button class="outline-button" type="button" @click="applyFdeDeliveryDemo">填充低碳材料案例</button></div><div v-if="!projectMatchResult" class="fde-report-empty"><div class="empty-illustration">◈</div><h3>等待 FDE 交付结果</h3><p>在“客户需求”中创建低碳建筑材料项目并运行需求匹配后，这里会自动汇总真实结果。</p><button class="primary-card-action" type="button" @click="openWorkspaceView('projects')">前往客户需求中心</button></div><div v-else class="fde-report-sheet"><header><span>ResearchOS · 科研合作方案</span><h3>{{ projectMatchResult.projectName }}</h3><p>{{ projectMatchResult.enterprise_requirement }}</p></header><section><b>01</b><div><h4>客户需求理解</h4><p>{{ projectMatchResult.enterprise_requirement }}</p></div></section><section><b>02</b><div><h4>实验室能力匹配</h4><ul><li v-for="item in projectMatchResult.lab_capability_match" :key="item">{{ item }}</li></ul></div></section><section><b>03</b><div><h4>技术路线与方案建议</h4><ul><li v-for="item in projectMatchResult.technical_solution_suggestions" :key="item">{{ item }}</li></ul></div></section><section><b>04</b><div><h4>创新机会</h4><p v-if="researchOsTaskResult?.innovation_opportunities">{{ researchOsTaskResult.innovation_opportunities }}</p><p v-else>运行 Research Master 的“创新发现 Agent”后将在此展示基于资料的创新机会。</p></div></section><section><b>05</b><div><h4>成果规划</h4><dl><template v-for="(value,key) in projectMatchResult.expected_outcome_plan" :key="key"><dt>{{ key }}</dt><dd>{{ Array.isArray(value) ? value.join('、') : value }}</dd></template></dl></div></section><section class="fde-evidence"><b>06</b><div><h4>分析依据</h4><p>以下章节级片段支撑客户需求匹配、技术路线与成果规划建议。</p><ul><li v-for="source in projectMatchResult.sources || []" :key="source.paper_id + source.section">{{ source.paper_title }} · {{ documentTypeLabel(source.document_type) }} · {{ source.section }}</li></ul><p v-if="!(projectMatchResult.sources || []).length">现有团队资料不足，暂无可展示的分析依据。</p></div></section><footer>{{ projectMatchResult.boundary_note }}</footer></div></section>

      <section v-if="activeWorkspaceView === 'projects' && selectedOutcomeProjectId" class="project-outcome-preview" aria-label="项目成果路径">
        <div class="decision-loop-heading"><div><p class="section-kicker">PROJECT OUTCOME PATH</p><h3>成果路径</h3><p>项目成果从规划到知识资产整理的当前状态。</p></div><select v-model="selectedOutcomeProjectId" @change="loadProjectOutcomes"><option v-for="project in researchProjects" :key="project.id" :value="project.id">{{ project.name }}</option></select></div>
        <div v-if="!projectOutcomes.length" class="decision-loop-empty"><b>尚无成果路径记录</b><p>可在“科研成果”中新增论文、专利、技术报告或实验成果。</p></div><ol v-else class="project-outcome-mini-path"><li v-for="outcome in projectOutcomes" :key="outcome.id"><i></i><div><b>{{ outcome.outcome_type }} · {{ outcome.title }}</b><span>{{ outcome.status }} · 知识状态：{{ outcome.knowledge_status }}</span></div></li></ol><button class="outline-button" type="button" @click="openWorkspaceView('outcome-center')">管理科研成果</button>
      </section>

      <section v-if="activeWorkspaceView === 'tasks' && researchOsTaskResult" class="agent-action-bridge" aria-label="将科研任务建议转为行动">
        <div><p class="section-kicker">RESEARCH MASTER → ACTION CENTER</p><h3>将创新与项目规划建议交由负责人确认</h3><p>以下条目来自已执行的 Research Master 协作结果；未运行任务或资料不足时不会生成建议。</p></div>
        <div v-if="actionableTaskSuggestions.length" class="agent-suggestion-list"><article v-for="item in actionableTaskSuggestions" :key="item.sourceAgent + item.title"><p><small>{{ item.sourceAgent }}</small>{{ item.title }}</p><button class="outline-button" type="button" :disabled="actionLoading" @click="createActionFromSuggestion(item.title, item.sourceAgent, researchOsTaskResult.executive_summary || researchOsGoal, researchOsTaskResult.sources)">纳入行动</button></article></div><p v-else class="demo-boundary">当前任务尚未返回可转化的行动建议；请先运行包含 Innovation Agent 或 Project Agent 的科研任务。</p>
      </section>

      <section v-if="activeWorkspaceView === 'projects' && projectMatchResult" class="agent-action-bridge" aria-label="将项目建议转为行动">
        <div><p class="section-kicker">PROJECT AGENT → ACTION CENTER</p><h3>将有依据的方案建议纳入下一步行动</h3><p>仅把当前 Project Agent 已生成的技术建议转为待人工确认事项，并保留资料来源。</p></div>
        <div class="agent-suggestion-list"><article v-for="suggestion in projectMatchResult.technical_solution_suggestions || []" :key="suggestion"><p>{{ suggestion }}</p><button class="outline-button" type="button" :disabled="actionLoading" @click="createActionFromSuggestion(suggestion, 'Project Agent', projectMatchResult.enterprise_requirement, projectMatchResult.sources, selectedOutcomeProjectId)">纳入行动</button></article></div>
      </section>

      <section v-if="activeWorkspaceView === 'outcome-center'" class="decision-loop-center output-studio" aria-label="Research Output Studio">
        <div class="dashboard-heading"><div><p class="section-kicker">RESEARCH OUTPUT STUDIO</p><h2>把 Evidence 转化为待审核的研究交付物。</h2><p>Literature Review、Experiment Plan 与 Project Proposal 都只基于已有资料与人工确认推进。</p></div><button class="outline-button" type="button" @click="openWorkspaceView('projects')">查看科研项目</button></div>
        <p v-if="actionError || outcomeError" class="error-alert"><span>!</span>{{ actionError || outcomeError }}</p>
        <section class="decision-loop-panel"><div class="decision-loop-heading"><div><p class="section-kicker">HUMAN-IN-THE-LOOP</p><h3>AI 建议与人工确认</h3></div><button class="outline-button" type="button" :disabled="actionLoading" @click="loadResearchActions()">{{ actionLoading ? '刷新中…' : '刷新行动' }}</button></div><div v-if="!researchActions.length && !actionLoading" class="decision-loop-empty"><b>暂无待确认行动</b><p>在 FDE 解决方案报告或 Research Master 任务结果中，将有证据支撑的建议加入行动中心。</p></div><article v-for="action in researchActions" :key="action.id" class="research-action-card"><header><div><span>{{ action.status }}</span><strong>{{ action.source_agent }}</strong></div><time>{{ formatLibraryDate(action.created_at) }}</time></header><h4>{{ action.title }}</h4><p>{{ action.description || '待负责人根据该建议安排下一步行动。' }}</p><details class="action-evidence-details"><summary>查看分析依据</summary><section><h5>建议形成依据</h5><p>{{ action.rationale || '暂无可读分析说明。' }}</p></section><section><h5>Evidence 引用</h5><div v-if="action.evidence_refs?.length" class="action-evidence-list"><article v-for="ref in action.evidence_refs" :key="ref.evidence_id || ref.title + ref.detail"><b>{{ ref.evidence_id || '未提供 Evidence ID' }}</b><p>来源：{{ ref.source || ref.title || '未提供来源文件' }}</p><p>章节：{{ ref.chapter || ref.detail || '未提供章节' }}</p><p>来源 Agent：{{ ref.agent || action.source_agent }}</p><p v-if="ref.score !== null && ref.score !== undefined">匹配度：{{ (Number(ref.score) * 100).toFixed(0) }}%</p><p v-else>匹配度：暂无可验证资料</p></article></div><p v-else>暂无可验证资料。该建议需先补充资料或人工核验后再推进。</p><button v-if="action.evidence_refs?.length" type="button" class="text-button" @click="openWorkspaceView('evidence')">查看 Evidence Center →</button></section></details><section class="action-next-step"><h5>下一步行动</h5><select :value="action.status" @change="updateResearchAction(action, { status: $event.target.value })"><option>待执行</option><option>进行中</option><option>已完成</option><option>已取消</option></select></section><section class="action-confirmation"><h5>人工确认</h5><div class="action-controls"><input v-model="decisionNotes[action.id]" placeholder="确认说明（可选）" /><button type="button" @click="recordResearchDecision(action, '已采纳')">采纳建议</button><button type="button" @click="recordResearchDecision(action, '已修改')">修改后采纳</button><button type="button" class="quiet-danger" @click="recordResearchDecision(action, '已拒绝')">拒绝</button></div></section><footer v-if="decisionForAction(action.id)">人工决定：<b>{{ decisionForAction(action.id).decision }}</b><span v-if="decisionForAction(action.id).note"> · {{ decisionForAction(action.id).note }}</span></footer></article></section>
        <section class="decision-loop-panel outcome-panel"><div class="decision-loop-heading"><div><p class="section-kicker">PROJECT OUTCOMES</p><h3>成果路径</h3></div><select v-model="selectedOutcomeProjectId" @change="loadProjectOutcomes"><option value="">选择科研项目</option><option v-for="project in researchProjects" :key="project.id" :value="project.id">{{ project.name }}</option></select></div><div v-if="!researchProjects.length" class="decision-loop-empty"><b>尚未创建科研项目</b><p>先在科研项目中心创建项目，再规划成果路径。</p></div><template v-else><form class="outcome-create-form" @submit.prevent="createProjectOutcome"><select v-model="outcomeForm.outcome_type"><option>论文</option><option>专利</option><option>技术报告</option><option>实验成果</option></select><input v-model="outcomeForm.title" placeholder="成果名称，例如：低碳材料耐久性验证技术报告" /><select v-model="outcomeForm.status"><option>规划中</option><option>进行中</option><option>已完成</option><option>已提交</option><option>已归档</option></select><textarea v-model="outcomeForm.description" rows="2" placeholder="成果说明（可选）"></textarea><select v-model="outcomeForm.source_action_id"><option value="">来源行动（可选）</option><option v-for="action in researchActions.filter(item => !item.project_id || item.project_id === selectedOutcomeProjectId)" :key="action.id" :value="action.id">{{ action.title }}</option></select><button class="primary-card-action" type="submit" :disabled="outcomeLoading">{{ outcomeLoading ? '保存中…' : '新增成果' }}</button></form><div v-if="!projectOutcomes.length && !outcomeLoading" class="decision-loop-empty"><b>当前项目尚无成果记录</b><p>成果状态用于管理交付过程；“已沉淀”仅记录知识资产整理状态，不会自动写入 RAG 索引。</p></div><div class="outcome-path"><article v-for="outcome in projectOutcomes" :key="outcome.id"><i></i><div><span>{{ outcome.outcome_type }} · {{ outcome.status }}</span><h4>{{ outcome.title }}</h4><p>{{ outcome.description || '暂无成果说明。' }}</p><p v-if="outcome.source_action_id" class="outcome-source-action">来源行动：{{ actionTitle(outcome.source_action_id) }}</p><p v-else class="outcome-source-action">来源行动：未关联</p><div class="outcome-controls"><select :value="outcome.status" @change="updateProjectOutcome(outcome, { status: $event.target.value })"><option>规划中</option><option>进行中</option><option>已完成</option><option>已提交</option><option>已归档</option></select><select :value="outcome.knowledge_status" @change="updateOutcomeKnowledgeStatus(outcome, $event.target.value)"><option>未沉淀</option><option>待整理</option><option>已沉淀</option></select><button type="button" class="quiet-danger" @click="deleteProjectOutcome(outcome)">删除</button></div></div></article></div><p class="demo-boundary">知识资产状态仅记录成果整理准备度。完成资料整理、文本解析与索引后，才可按现有知识库流程进入检索范围。</p></template></section>
      </section>

      <section v-if="activeWorkspaceView === 'outcome-center' && researchActions.length" class="decision-project-bridge" aria-label="Evidence、Decision 与 Project 关联">
        <p class="section-kicker">EVIDENCE → DECISION → PROJECT</p>
        <h3>人工确认后推进项目</h3>
        <p>建议、依据与人工决定保留在行动中心；只有采纳后才可预填项目，不会自动创建项目或替代负责人判断。</p>
        <article v-for="action in researchActions" :key="'bridge-' + action.id">
          <div><b>{{ action.title }}</b><small>Evidence：{{ action.evidence_refs?.length || 0 }} 条 · {{ decisionForAction(action.id)?.decision || '待确认' }}</small></div>
          <div class="action-controls"><button type="button" class="outline-button" @click="recordResearchDecision(action, '需补充证据')">请求补充 Evidence</button><button type="button" class="primary-card-action" :disabled="!['已采纳', '已修改'].includes(decisionForAction(action.id)?.decision)" @click="prepareProjectFromDecision(action)">创建项目草案</button></div>
        </article>
      </section>

      <section v-if="activeWorkspaceView === 'system'" class="system-center" aria-label="系统状态中心">
        <div class="dashboard-heading"><div><p class="section-kicker">SYSTEM STATUS CENTER</p><h2>系统状态中心</h2><p>{{ systemStatus?.version || 'ResearchOS v3.0' }} · {{ systemStatus?.platform_name || 'AI科研创新决策平台' }}</p></div><button class="outline-button" type="button" :disabled="systemStatusLoading" @click="loadSystemStatus">{{ systemStatusLoading ? '检查中…' : '刷新状态' }}</button></div>
        <p v-if="systemStatusError" class="error-alert"><span>!</span>{{ systemStatusError }}</p>
        <div v-if="systemStatus" class="system-status-grid"><article v-for="service in systemStatus.services" :key="service.id"><header><span :class="service.status">{{ service.status === 'ready' || service.status === 'configured' ? '正常' : service.status === 'empty' ? '待初始化' : '需配置' }}</span><b>{{ service.name }}</b></header><p>{{ service.detail }}</p></article></div>
        <section class="workflow-diagnostics-panel runtime-dashboard"><div class="result-section-heading"><div><p class="section-kicker">PRODUCTION RUNTIME</p><h3>Runtime Dashboard</h3><p>队列、Worker 与基础设施状态来自当前运行时；不展示 Prompt、CoT 或 Secret。</p></div><button class="outline-button" type="button" :disabled="runtimeStatusLoading" @click="loadRuntimeStatus">{{ runtimeStatusLoading ? 'Checking…' : 'Refresh runtime' }}</button></div><div v-if="runtimeStatus" class="diagnostic-check-grid"><article><span>QUEUE</span><h4>{{ runtimeStatus.queue_length }}</h4><p>Queued tasks</p></article><article><span>WORKER</span><h4>{{ runtimeStatus.worker_status }}</h4><p>{{ runtimeStatus.running_agents }} running · {{ runtimeStatus.failed_tasks }} failed</p></article><article><span>RETRY</span><h4>{{ runtimeStatus.retry_count }}</h4><p>Average duration {{ runtimeStatus.average_duration }}s</p></article><article v-for="(service, name) in runtimeStatus.services" :key="name"><span :class="service.status">{{ service.status }}</span><h4>{{ name }}</h4><p>{{ service.detail }}</p></article></div><p v-else class="quiet-note">Runtime Dashboard 暂不可用；不会影响已有研究能力。</p></section>
        <section v-if="llmRuntimeStatus" class="workflow-diagnostics-panel runtime-dashboard"><div class="result-section-heading"><div><p class="section-kicker">LLM NATIVE RUNTIME</p><h3>LLM Runtime Dashboard</h3><p>只展示模型调用元数据；计划、工具与权限仍由系统校验。</p></div></div><div class="diagnostic-check-grid"><article><span>MODEL</span><h4>{{ llmRuntimeStatus.model.model }}</h4><p>{{ llmRuntimeStatus.model.provider }} · {{ llmRuntimeStatus.model.configured ? 'enabled' : 'disabled' }}</p></article><article><span>REQUESTS</span><h4>{{ llmRuntimeStatus.requests }}</h4><p>Validated planning calls</p></article><article><span>LATENCY</span><h4>{{ llmRuntimeStatus.average_latency }}s</h4><p>Average observed latency</p></article><article><span>FAILURES</span><h4>{{ llmRuntimeStatus.failures }}</h4><p>No prompt, response, CoT or secret stored</p></article></div></section>
        <section class="workflow-diagnostics-panel"><div class="result-section-heading"><div><p class="section-kicker">REAL WORKFLOW READINESS</p><h3>真实资料闭环检查</h3><p>只检查已有资料、索引与服务配置；不会生成样例论文、证据或科研结论。</p></div><button class="outline-button" type="button" :disabled="diagnosticsLoading" @click="loadWorkflowDiagnostics">{{ diagnosticsLoading ? '检查中…' : '重新检查' }}</button></div><p v-if="diagnosticsError" class="error-alert"><span>!</span>{{ diagnosticsError }}</p><div v-if="workflowDiagnostics" class="diagnostic-summary"><b :class="workflowDiagnostics.overall">{{ workflowDiagnostics.overall }}</b><span>{{ workflowDiagnostics.data_boundary }}</span></div><div v-if="workflowDiagnostics" class="diagnostic-check-grid"><article v-for="check in workflowDiagnostics.checks" :key="check.id"><span :class="check.status">{{ check.status }}</span><h4>{{ check.name }}</h4><p>{{ check.detail }}</p></article></div></section>
        <section class="demo-knowledge-panel"><div><p class="section-kicker">DEMO KNOWLEDGE BASE</p><h3>低碳建筑材料案例资料</h3><p>用于比赛现场讲解知识库、项目资料和产学研协作流程。</p></div><button class="primary-card-action" type="button" @click="initializeDemoKnowledge">{{ demoKnowledgeInitialized ? 'Demo资料已加载' : '初始化 Demo 知识库' }}</button><div v-if="visibleDemoKnowledgeAssets.length" class="demo-asset-grid"><article v-for="asset in visibleDemoKnowledgeAssets" :key="asset.title"><span>{{ asset.status }}</span><h4>{{ asset.title }}</h4><small>{{ asset.type }}</small><p>{{ asset.detail }}</p></article></div><p class="demo-boundary">这些是明确标注的界面展示资料，不会自动写入真实论文库、FAISS 索引或作为 Agent 的科研证据。需要真实分析时，请上传实际可解析的资料。</p></section>
        <section class="activity-log-panel"><div class="result-section-heading"><div><p class="section-kicker">ACTIVITY LOG</p><h3>用户操作日志</h3></div><span>{{ activityLogs.length }} 条</span></div><div v-if="!activityLogs.length" class="activity-empty">暂无操作记录。创建任务、执行 Agent、生成报告或更新项目后会在此显示。</div><ol v-else class="activity-list"><li v-for="item in activityLogs" :key="item.created_at + item.action"><b>{{ item.action }}</b><span>{{ item.detail }}</span><time>{{ formatLibraryDate(item.created_at) }}</time></li></ol></section>
        <section class="agent-analytics-panel"><div class="result-section-heading"><div><p class="section-kicker">AGENT ANALYTICS</p><h3>Execution quality & observability</h3></div><button class="outline-button" type="button" @click="loadAgentAnalytics">Refresh</button></div><p v-if="adaptiveAnalytics" class="quiet-note">Adaptive Missions {{ adaptiveAnalytics.adaptive_missions }} · Replan rate {{ adaptiveAnalytics.replan_rate }} · Avg iterations {{ adaptiveAnalytics.average_iterations }} · Evidence recovery {{ adaptiveAnalytics.evidence_recovery_rate }}% · Verification recovery {{ adaptiveAnalytics.verification_recovery_rate }}%</p><article v-for="metric in agentAnalytics" :key="metric.agent_name"><b>{{ metric.agent_name }}</b><span>{{ metric.total_tasks }} tasks · {{ metric.success_rate }}% success · {{ metric.avg_duration }}s avg · {{ metric.avg_evidence_count }} Evidence</span></article><p v-if="!agentAnalytics.length">尚无持久化 Agent Trace；运行新的 Mission 后将显示可审计统计。</p></section>
        <section class="agent-analytics-panel"><div class="result-section-heading"><div><p class="section-kicker">COPILOT ANALYTICS</p><h3>AI Copilot usage overview</h3></div><button class="outline-button" type="button" @click="loadCopilotAnalytics">Refresh</button></div><template v-if="copilotAnalytics"><p class="quiet-note">Sessions {{ copilotAnalytics.sessions || 0 }} · Created Missions {{ copilotAnalytics.created_missions || 0 }} · Completion {{ copilotAnalytics.completion_rate || '0%' }} · Average session time {{ copilotAnalytics.average_session_time || 'not available' }}</p><article v-for="(count, intent) in (copilotAnalytics.intent_distribution || {})" :key="intent"><b>{{ intent }}</b><span>{{ count }} classified session message{{ count === 1 ? '' : 's' }}</span></article></template><p v-else>暂无 Copilot 会话统计；发起 Mission 后可查看真实使用概览。</p></section>
        <section class="agent-analytics-panel"><div class="result-section-heading"><div><p class="section-kicker">DOCUMENT ANALYTICS</p><h3>Enterprise input understanding</h3></div><button class="outline-button" type="button" @click="loadDocumentAnalytics">Refresh</button></div><template v-if="documentAnalytics"><p class="quiet-note">Uploaded {{ documentAnalytics.uploaded_files }} · Processed {{ documentAnalytics.processed_files }} · Failed {{ documentAnalytics.failed_files }} · Requirement drafts {{ documentAnalytics.requirement_extraction_count }}</p><p>Parse success {{ documentAnalytics.input_understanding_score?.parse_success_rate }}% · Requirement coverage {{ documentAnalytics.input_understanding_score?.requirement_coverage }} · Confirmation modifications {{ documentAnalytics.input_understanding_score?.user_confirmation_modifications }}</p><small>{{ documentAnalytics.boundary }}</small></template><p v-else>暂无已上传客户资料。</p></section>
        <section class="agent-analytics-panel"><div class="result-section-heading"><div><p class="section-kicker">AGENT MEMORY CENTER</p><h3>Reviewable memory summaries</h3></div><button class="outline-button" type="button" @click="loadAgentMemories">Refresh</button></div><article v-for="memory in agentMemories" :key="memory.id"><b>{{ memory.agent_name }} · {{ memory.memory_type }}</b><span>{{ memory.content_summary }}</span><small>{{ memory.status }} · Mission {{ memory.source_mission_id || 'N/A' }}</small><button class="text-button" type="button" @click="deleteAgentMemory(memory.id)">Delete</button></article><p v-if="!agentMemories.length">暂无 Agent Memory。任务完成后的摘要必须经人工确认后才可作为可复用 Memory。</p></section>
        <p class="demo-boundary">操作日志仅保存在当前浏览器的 localStorage 中，用于现场演示；清除浏览器数据后会被移除。</p>
      </section>

      <section v-if="activeWorkspaceView === 'system' && connectorAnalytics" class="mission-tool-trace" aria-label="Connector Analytics"><p class="section-kicker">TOOL ANALYTICS</p><h3>Read-only Connector Operations</h3><article><b>{{ connectorAnalytics.connectors }} connectors</b><small>{{ connectorAnalytics.tool_usage_count }} calls · {{ connectorAnalytics.failures }} failures</small><p>{{ connectorAnalytics.connector_success_rate }}% success · {{ connectorAnalytics.average_duration_ms }}ms average · {{ connectorAnalytics.data_source_usage }} data sources</p></article></section>

      <section v-if="activeWorkspaceView === 'system' && collaborationAnalytics" class="mission-tool-trace" aria-label="Agent Collaboration Analytics"><p class="section-kicker">AGENT COLLABORATION ANALYTICS</p><h3>Summary-only collaboration health</h3><article><b>{{ collaborationAnalytics.message_count }} messages</b><small>{{ collaborationAnalytics.average_collaboration_round }} average round · {{ collaborationAnalytics.agent_participation }} participants</small><p>{{ collaborationAnalytics.conflict_count }} conflicts · {{ collaborationAnalytics.message_completion_rate }}% completed messages</p></article></section>

      <section v-if="activeWorkspaceView === 'timeline'" class="agent-timeline-center" aria-label="Agent执行时间线">
        <div class="dashboard-heading"><div><p class="section-kicker">AGENT TIMELINE</p><h2>AI 团队执行时间线</h2><p>展示面向用户的任务协作摘要，而非模型内部思维过程。</p></div><button class="outline-button" type="button" @click="openWorkspaceView('tasks')">运行科研任务</button></div>
        <div class="timeline-board"><article v-for="(item, index) in agentTimeline" :key="item.agent + item.action + index" :class="item.status"><span class="timeline-index">{{ index + 1 }}</span><div><p>{{ item.agent }}</p><h3>{{ item.action }}</h3><small>{{ item.summary }}</small></div><b>{{ item.status === 'completed' ? '已完成' : item.status === 'pending' ? '待运行' : item.status }}</b></article></div>
        <p class="demo-boundary">时间线仅反映 ResearchOS 已执行或待执行的产品流程；专项结论需在 Agent 实际运行并检索到团队资料后生成。</p>
      </section>

      <section v-if="activeWorkspaceView === 'evidence'" class="evidence-center" aria-label="Research Evidence Center">
        <div class="dashboard-heading"><div><p class="section-kicker">RESEARCH EVIDENCE CENTER</p><h2>科研证据中心</h2><p>将 Agent 输出关联到已上传科研资料的章节级片段，帮助科研人员复核分析依据。</p></div><button class="outline-button" type="button" :disabled="evidenceLoading" @click="loadEvidenceCenter">{{ evidenceLoading ? '加载中…' : '刷新证据' }}</button></div>
        <p v-if="evidenceError" class="error-alert"><span>!</span>{{ evidenceError }}</p>
        <div v-if="!evidenceCenterItems.length && !evidenceLoading" class="delivery-empty"><div class="empty-illustration">⌘</div><h3>暂无可展示的证据片段</h3><p>请先上传并完成科研资料索引，或运行科研任务、项目需求匹配、实验室画像生成。</p><button class="outline-button" type="button" @click="openWorkspaceView('knowledge')">前往科研知识库</button></div>
        <div v-else class="evidence-card-grid"><article v-for="(item, index) in evidenceCenterItems" :key="item.paper_id + '-' + item.section + '-' + item.related_agent + '-' + index" class="evidence-center-card"><header><span>{{ documentTypeLabel(item.document_type) }}</span><b>{{ item.related_agent }}</b></header><h3>{{ item.paper_title }}</h3><p class="evidence-meta">来源文件：{{ item.source_file }} · 章节：{{ item.section }}</p><blockquote>{{ item.content }}</blockquote><footer><span>分析依据：{{ item.basis }}</span><em v-if="item.score !== undefined">匹配度 {{ Number(item.score).toFixed(4) }}</em></footer></article></div>
        <p class="demo-boundary">证据中心展示的是资料章节级摘要，不是精准页码引用或完整原文溯源；资料不足时，系统不应把推测当作科研事实。</p>
      </section>

      <section v-if="activeWorkspaceView === 'lab-profile'" class="lab-profile-center" aria-label="实验室数字画像">
        <div class="dashboard-heading"><div><p class="section-kicker">DIGITAL LAB PROFILE</p><h2>实验室数字画像</h2><p>基于团队已上传资料与项目记录，形成可核验的科研能力展示入口。</p></div><button class="primary-card-action" type="button" :disabled="labProfileLoading" @click="generateLabProfile">{{ labProfileLoading ? '生成中…' : '生成能力画像' }}</button></div>
        <div class="lab-profile-overview"><article><span>研究方向</span><strong>{{ labProfile?.research_directions?.length ?? 0 }}</strong><small>来自已检索资料</small></article><article><span>科研资料</span><strong>{{ researchBi?.research_assets?.papers ?? 0 }}</strong><small>已入库资产</small></article><article><span>知识片段</span><strong>{{ researchBi?.research_assets?.knowledge_chunks ?? 0 }}</strong><small>支持检索引用</small></article><article><span>科研项目</span><strong>{{ researchBi?.research_assets?.projects ?? 0 }}</strong><small>生命周期记录</small></article></div>
        <div v-if="!labProfile && !labProfileLoading" class="delivery-empty"><div class="empty-illustration">◌</div><h3>等待基于资料生成的实验室画像</h3><p>系统不会预设实验室能力。上传并完成索引的资料越充分，画像越有可复核依据。</p></div>
        <div v-else-if="labProfile" class="lab-profile-result"><p class="profile-summary">{{ labProfile.profile_summary }}</p><div class="lab-profile-grid"><article><h3>研究方向</h3><ul><li v-for="item in labProfile.research_directions" :key="item">{{ item }}</li></ul></article><article><h3>核心能力</h3><ul><li v-for="item in labProfile.core_capabilities" :key="item">{{ item }}</li></ul></article><article><h3>成果资产</h3><ul><li v-for="item in labProfile.research_outputs" :key="item">{{ item }}</li></ul></article><article><h3>企业合作推荐</h3><ul><li v-for="item in labProfile.collaboration_directions" :key="item">{{ item }}</li></ul></article></div><section class="digital-radar"><h3>科研能力覆盖度</h3><div v-if="researchBi?.capability_radar?.length" class="radar-list"><div v-for="item in researchBi.capability_radar" :key="item.name"><span>{{ item.name }}</span><i><b :style="{ width: item.score + '%' }"></b></i><em>{{ item.score }}</em></div></div><p>覆盖度来自当前本地资料、知识片段、项目与成果规划数量，不代表实验室真实评级或外部排名。</p></section><section class="evidence-inline"><h3>画像分析依据</h3><ul><li v-for="source in labProfile.sources || []" :key="source.paper_id + source.section">{{ source.paper_title }} · {{ documentTypeLabel(source.document_type) }} · {{ source.section }}</li></ul></section><p class="trace-boundary">{{ labProfile.boundary_note }}</p></div>
      </section>

      <section v-if="activeWorkspaceView === 'commercial'" class="commercial-center" aria-label="ResearchOS商业方案">
        <div class="dashboard-heading"><div><p class="section-kicker">COMMERCIALIZATION VIEW</p><h2>ResearchOS 商业方案</h2><p>面向科研知识管理、科研协作和产学研需求匹配的产品化表达。</p></div></div>
        <div class="commercial-plan-grid"><article><span>实验室版</span><h3>服务高校课题组</h3><ul><li>科研知识库</li><li>AI 科研助手</li><li>项目与成果管理</li></ul><p>价值：减少资料整理成本，沉淀可复用的团队知识。</p></article><article><span>学院版</span><h3>服务科研管理部门</h3><ul><li>多实验室管理入口</li><li>科研资产分析</li><li>科研能力画像</li></ul><p>价值：形成面向管理者的科研资产与能力展示视图。</p></article><article><span>产学研合作版</span><h3>服务企业研发部门</h3><ul><li>企业需求匹配</li><li>高校能力发现</li><li>联合研发方案生成</li></ul><p>价值：支持从需求澄清到科研合作方案的协作交付。</p></article></div>
        <section class="commercial-value-strip"><div><b>客户价值</b><span>更快理解可合作的科研能力与项目风险。</span></div><div><b>产品价值</b><span>把分散科研资料转化为有证据支撑的协作入口。</span></div><div><b>商业模式</b><span>按实验室、学院或产学研协作场景提供产品与交付服务。</span></div></section><p class="demo-boundary">此页面用于展示产品定位与可服务场景，不代表已验证的市场规模、客户数量、收入或生产部署案例。</p>
      </section>

      <section v-if="activeWorkspaceView === 'delivery'" class="delivery-center" aria-label="项目交付中心">
        <div class="dashboard-heading"><div><p class="section-kicker">PROJECT DELIVERY CENTER</p><h2>项目交付中心</h2><p>以项目生命周期组织需求、技术路线、成果规划与 FDE 解决方案交付。</p></div><button class="primary-card-action" type="button" @click="startDemoMode">载入比赛案例</button></div>
        <div v-if="!researchProjects.length" class="delivery-empty"><div class="empty-illustration">◌</div><h3>尚无项目交付记录</h3><p>载入低碳建筑材料案例后，在客户需求中心创建项目，即可开始形成真实交付物。</p><button class="outline-button" type="button" @click="openWorkspaceView('projects')">前往客户需求中心</button></div>
        <div v-else class="delivery-list"><article v-for="project in researchProjects" :key="project.id" class="delivery-card"><div class="delivery-card-heading"><div><span class="paper-status">{{ projectDeliveryStage(project) }}</span><h3>{{ project.name }}</h3></div><time>更新于 {{ formatLibraryDate(project.updated_at) }}</time></div><div class="delivery-meta"><div><span>项目阶段</span><b>{{ projectDeliveryStage(project) }}</b></div><div><span>协同负责人</span><b>项目负责人 · ResearchOS Project Agent</b></div><div><span>当前状态</span><b>{{ project.status || 'active' }}</b></div></div><section><h4>当前交付物</h4><ul><li>企业需求：{{ project.enterprise_requirement || '待补充' }}</li><li>技术路线：{{ project.technology_route || '待通过能力匹配生成' }}</li><li>论文规划：{{ project.paper_plan || '待规划' }}</li><li>专利规划：{{ project.patent_plan || '待规划' }}</li><li>成果管理：{{ project.outcome_management || '待规划' }}</li></ul></section><footer><button class="outline-button" type="button" :disabled="projectMatching" @click="runProjectMatch(project)">生成 / 更新交付物</button><button class="primary-card-action" type="button" @click="openWorkspaceView('fde-report')">查看 FDE 报告</button></footer></article></div>
      </section>

      <section v-if="activeWorkspaceView === 'customer-value'" class="customer-value-center" aria-label="客户价值总结">
        <div class="dashboard-heading"><div><p class="section-kicker">FDE VALUE SUMMARY</p><h2>客户价值总结</h2><p>把资料理解、科研协作和成果规划放入同一条可沟通的交付路径。</p></div><button class="outline-button" type="button" @click="openWorkspaceView('fde-report')">查看方案报告</button></div>
        <div class="customer-value-grid"><article><span>企业价值</span><h3>更快完成需求澄清</h3><p>基于项目资料整理技术关注点、实施风险和后续沟通问题，辅助企业与实验室对齐合作范围。</p></article><article><span>实验室价值</span><h3>沉淀可复用知识资产</h3><p>将论文与科研资料纳入知识库，支持能力匹配、技术路线讨论和研究成果规划。</p></article><article><span>高校价值</span><h3>形成协同交付路径</h3><p>用项目生命周期串联企业需求、研究任务、论文专利规划与阶段性成果管理。</p></article></div>
        <p class="demo-boundary">以上为产品价值设计与协作方式说明，不代表已验证的量化业务成效；具体结论须结合项目资料与实际验收确认。</p>
      </section>

      <div v-show="activeWorkspaceView === 'assistant'" class="assistant-workspace-view">

      <details class="quick-workspace compact-details" aria-label="快捷研究任务"><summary>快捷研究任务</summary>
        <div><p class="section-kicker">AI INSIGHT WORKSPACE</p><h2>今天我要完成</h2><p>选择一个业务任务，工作空间会自动配置 AI 员工、场景和目标。</p></div>
        <div class="quick-task-options"><button v-for="item in quickWorkspaceTasks" :key="item.id" type="button" :class="{ active: selectedQuickTask === item.id }" @click="selectQuickTask(item)"><i></i>{{ item.name }}</button></div>
      </details>

      <p v-if="errorMessage" class="error-alert" role="alert">
        <span>!</span>{{ errorMessage }}
      </p>

      <section class="workspace-grid">
        <aside class="control-panel">
          <div class="panel-heading">
            <p class="section-kicker">WORKSPACE</p>
            <h2>我的AI工作空间</h2>
          </div>

          <details class="employee-profile compact-details" aria-label="AI助手状态"><summary>AI 助手状态 · {{ selectedRole.name }}</summary>
            <div class="employee-profile-heading"><div><p class="section-kicker">AI EMPLOYEE STATUS</p><h3>{{ selectedRole.name }}</h3></div><span class="employee-online"><i></i> 在线</span></div>
            <p class="profile-label">核心能力</p><div class="profile-capabilities"><span v-for="item in selectedRole.capabilities" :key="item">{{ item }}</span></div>
            <div class="employee-task-status"><span>当前任务状态</span><b :class="{ active: loading }">{{ loading ? '正在执行任务' : (result ? '已完成业务交付' : '等待接收任务') }}</b><small>{{ task || '请选择或输入业务目标' }}</small></div>
            <p class="profile-label">历史任务</p>
            <ul v-if="roleHistory.length" class="profile-history"><li v-for="item in roleHistory" :key="item.completedAt"><b>✓</b><span>{{ item.task }}</span><small>{{ item.fileName }}</small></li></ul>
            <p v-else class="profile-empty">完成真实文档分析后，最近任务会保存在当前浏览器。</p>
          </details>

          <section class="role-section" aria-label="用户角色选择">
            <div class="step-label"><b>Step 1</b><label>选择 AI 员工</label></div>
            <div class="role-options">
              <button v-for="item in roleOptions" :key="item.id" type="button" class="role-option" :class="{ active: role === item.id }" @click="selectRole(item)">
                <strong>{{ item.name }}</strong><small>{{ item.description }}</small>
              </button>
            </div>
          </section>

          <details class="scenario-section compact-details" aria-label="更多分析设置"><summary>更多分析设置 · {{ selectedScenario.name }}</summary>
            <div class="step-label"><b>Step 2</b><label>选择分析场景</label><span>{{ selectedScenario.id }}</span></div>
            <div class="scenario-options">
              <button
                v-for="item in scenarioOptions"
                :key="item.id"
                type="button"
                class="scenario-option"
                :class="{ active: scenario === item.id }"
                @click="scenario = item.id"
              >
                <strong>{{ item.name }}</strong><small>{{ item.description }}</small>
              </button>
            </div>
          </details>

          <div class="task-section">
            <div class="label-row">
              <span class="step-label"><b>Step 3</b><label for="task">请输入你的目标</label></span>
              <button class="text-button" type="button" @click="resetTask">恢复默认</button>
            </div>
            <textarea id="task" v-model="task" rows="6" placeholder="例如：我要准备一次客户技术交流，需要分析该方案优势和风险"></textarea>
            <p class="field-hint">当前 AI 员工：{{ selectedRole.name }}。Agent 会据此规划分析重点和业务产物。</p>
          </div>

          <details class="demo-section compact-details" aria-label="预置演示案例"><summary>预置演示案例</summary>
            <div class="label-row"><label>Demo 展示模式</label><button class="full-demo-button" type="button" @click="applyFullDemo">3分钟体验Demo</button></div>
            <div class="demo-case-list"><button v-for="item in demoCases" :key="item.name" type="button" @click="applyDemo(item)">{{ item.name }}</button></div>
            <ol class="demo-flow"><li><b>01</b>理解客户需求</li><li><b>02</b>分析技术方案</li><li><b>03</b>判断风险</li><li><b>04</b>生成沟通方案</li><li><b>05</b>输出行动建议</li></ol>
          </details>

          <label class="upload-box" :class="{ 'has-file': selectedFile }" for="pdf-file">
            <input ref="fileInput" id="pdf-file" type="file" accept="application/pdf,.pdf" @change="onFileChange" />
            <span class="upload-icon">⇧</span>
            <strong>Step 4 · {{ selectedFile ? "更换 PDF 文档" : "上传 PDF 文档" }}</strong>
            <small>当前支持可提取文本的 PDF</small>
          </label>

          <div class="file-summary" v-if="selectedFile">
            <div class="file-badge">PDF</div>
            <div class="file-details">
              <strong>{{ selectedFile.name }}</strong>
              <span>{{ fileSizeLabel }}</span>
            </div>
            <span class="ready-dot"></span>
          </div>

          <div class="upload-status">
            <span>上传状态</span><strong :class="{ active: selectedFile }">{{ uploadStatus }}</strong>
          </div>

          <button class="analyze-button" :disabled="loading" @click="analyzeDocument">
            <span v-if="loading" class="spinner small-spinner"></span>
            {{ loading ? "正在分析文档..." : "开始 Agent 分析" }}
          </button>
          <button v-if="result" class="clear-button" type="button" @click="clearCurrentDocument">清空当前文档</button>
        </aside>

        <section class="result-panel">
          <div class="result-header">
            <div>
              <p class="section-kicker">DECISION REPORT</p>
              <h2>Step 5 · {{ reportTitle }}</h2>
            </div>
            <button v-if="result" class="outline-button" :disabled="loading || libraryAnalysisLoading" @click="analysisFromLibrary ? analyzeLibraryPaper(selectedLibraryPaper) : analyzeDocument">{{ libraryAnalysisLoading ? "正在重新分析…" : "重新分析" }}</button>
          </div>

          <div v-if="loading || libraryAnalysisLoading" class="loading-state">
            <div class="process-heading">
              <span class="spinner"></span>
              <div><h3>AI 正在生成研究洞察</h3><p>请求已发送，正在处理研究任务与文档资料。</p></div>
            </div>
            <ol class="loading-workflow" aria-label="分析过程提示"><li><i></i>分析研究问题</li><li><i></i>理解文档内容</li><li><i></i>筛选关键证据</li><li><i></i>生成结构化结果</li></ol>
            <p class="loading-boundary">这是非流式请求的阶段提示；最终执行摘要以接口返回的 Agent 工作流为准。</p>
          </div>

          <div v-else-if="!result" class="empty-state">
            <div class="empty-illustration">⌁</div>
            <h3>等待开始分析</h3>
            <p>选择场景、输入目标并上传 PDF 文档后，结果会显示在这里。</p>
          </div>

          <div v-else class="analysis-content">
            <section class="workspace-summary" aria-label="我的AI工作空间">
              <div><p class="section-kicker">MY AI WORKSPACE</p><h3>{{ selectedRole.workspaceName || selectedRole.name + '工作空间' }}</h3></div>
              <div class="workspace-summary-grid"><article><span>当前任务</span><p>{{ result.user_goal || result.user_task || result.task || task }}</p></article><article><span>当前资料</span><p>{{ analysisFromLibrary ? (selectedLibraryPaper?.filename || '论文库资料') : (selectedFile?.name || '已上传文档') }}</p></article><article><span>Agent状态</span><p>{{ analysisFromLibrary ? '已完成论文库资料分析与业务结果整理' : '已完成规划、文档分析与业务结果整理' }}</p></article></div>
              <p v-if="analysisFromLibrary" class="library-analysis-note">当前结果来自科研空间「我的论文库」，可继续在下方针对同一论文追问。</p>
            </section>

            <details v-if="agentTrace" class="agent-trace-summary advanced-details" aria-label="高级信息：AI如何完成这次分析">
              <summary>高级信息 · AI 如何完成这次分析</summary>
              <div class="agent-decision-heading"><div><p class="section-kicker">EXECUTION SUMMARY</p><h3>AI如何完成这次分析</h3></div><span class="agent-trace-status">执行摘要</span></div>
              <div class="trace-row"><span>用户目标</span><p>{{ agentTrace.user_goal }}</p></div>
              <div class="trace-row"><span>用户角色</span><p>{{ agentTrace.user_role }}</p></div>
              <div class="trace-row"><span>分析策略</span><p>{{ agentTrace.analysis_strategy }}</p></div>
              <div v-if="agentTrace.selected_tools?.length" class="trace-row"><span>已用能力</span><div class="task-chip-list"><b v-for="item in agentTrace.selected_tools" :key="item">{{ item }}</b></div></div>
              <div v-if="agentTrace.execution_steps?.length" class="trace-row trace-plan-row"><span>执行步骤</span><ol class="agent-execution-plan"><li v-for="step in agentTrace.execution_steps" :key="step"><i>✓</i>{{ step }}</li></ol></div>
              <p class="trace-boundary">此处展示的是后端真实执行流程摘要，不展示模型内部思维过程。</p>
            </details>

            <details v-if="agentWorkflow" class="agent-workflow compact-details" aria-label="AI执行过程"><summary>AI 执行过程</summary>
              <div class="agent-decision-heading"><div><p class="section-kicker">WORKFLOW PLAN</p><h3>AI员工执行过程</h3></div><span class="agent-trace-status">真实执行摘要</span></div>
              <div class="trace-row"><span>用户目标</span><p>{{ agentWorkflow.user_goal }}</p></div>
              <div class="trace-row"><span>当前角色</span><p>{{ agentWorkflow.user_role }}</p></div>
              <div v-if="agentWorkflow.planning_summary" class="trace-row"><span>规划说明</span><p>{{ agentWorkflow.planning_summary }}</p></div>
              <ol v-if="agentWorkflow.steps.length" class="workflow-step-list"><li v-for="(step, index) in agentWorkflow.steps" :key="step.name"><b>{{ String(index + 1).padStart(2, '0') }}</b><div><strong>{{ step.name }}</strong><p v-if="step.purpose">{{ step.purpose }}</p></div><span>{{ step.status === 'completed' ? '已完成' : step.status }}</span></li></ol>
              <p class="trace-boundary">展示的是后端真实工作流摘要，不展示模型内部思维过程。</p>
            </details>

            <details v-if="agentDecision" class="agent-decision advanced-details" aria-label="高级信息：Agent执行过程">
              <summary>高级信息 · Agent 原始任务信息</summary>
              <div class="agent-decision-heading">
                <div>
                  <p class="section-kicker">AGENT TRACE</p>
                  <h3>Agent执行过程</h3>
                </div>
                <span class="agent-trace-status">后端真实返回</span>
              </div>

              <div v-if="agentDecision.scenario" class="trace-row"><span>当前场景</span><p>{{ agentDecision.scenario }}</p></div>
              <div v-if="agentDecision.roleName" class="trace-row"><span>用户角色</span><p>{{ agentDecision.roleName }}</p></div>
              <div v-if="agentDecision.documentType" class="trace-row"><span>文档类型</span><p>{{ agentDecision.documentType }}</p></div>
              <div v-if="agentDecision.userIntent" class="trace-row"><span>用户意图</span><p>{{ agentDecision.userIntent }}</p></div>
              <div v-else-if="agentDecision.userTask" class="trace-row"><span>用户任务</span><p>{{ agentDecision.userTask }}</p></div>
              <div v-if="agentDecision.detectedTasks.length" class="trace-row">
                <span>任务识别</span>
                <div class="task-chip-list"><b v-for="item in agentDecision.detectedTasks" :key="item">{{ item }}</b></div>
              </div>
              <div v-if="agentDecision.decisionReason" class="trace-row"><span>决策原因</span><p>{{ agentDecision.decisionReason }}</p></div>
              <div v-if="agentDecision.executionPlan.length" class="trace-row trace-plan-row">
                <span>执行计划</span>
                <ol class="agent-execution-plan"><li v-for="step in agentDecision.executionPlan" :key="step"><i>✓</i>{{ step }}</li></ol>
              </div>
            </details>

            <details v-if="trustReport" class="trust-report compact-details" aria-label="结果可信度中心"><summary>可信度与依据</summary>
              <div class="trust-report-heading"><div><p class="section-kicker">TRUST CENTER</p><h3>结果可信度中心</h3></div><strong v-if="trustReport.confidenceScore !== null">{{ trustReport.confidenceScore }}<small>/100</small></strong></div>
              <p class="trust-note">该评分基于当前结构化结果的字段覆盖与缺失信息规则计算，不代表事实正确率。</p>
              <div class="trust-grid"><article><h4>信息依据</h4><ul><li v-for="item in trustReport.informationBasis" :key="item">{{ item }}</li></ul></article><article><h4>不确定性</h4><ul><li v-for="item in trustReport.uncertainties" :key="item">{{ item }}</li></ul></article><article><h4>验证建议</h4><ul><li v-for="item in trustReport.verificationSuggestions" :key="item">{{ item }}</li></ul></article></div>
            </details>

            <details v-if="valueEstimation" class="value-estimation compact-details" aria-label="业务价值说明"><summary>研究价值说明</summary>
              <div><p class="section-kicker">VALUE ESTIMATION</p><h3>业务价值说明</h3></div>
              <div class="value-estimation-grid"><article><h4>时间节省</h4><p>{{ valueEstimation.time_saved }}</p></article><article><h4>决策辅助</h4><p>{{ valueEstimation.decision_support }}</p></article><article><h4>应用场景</h4><p>{{ valueEstimation.application_scene }}</p></article></div>
              <p>仅描述定性价值，不虚构节省比例、准确率或业务收益数据。</p>
            </details>

            <details v-if="businessReport" class="business-report compact-details" aria-label="AI研究报告"><summary>研究报告</summary>
              <div class="business-report-heading"><div><p class="section-kicker">BUSINESS INSIGHT</p><h3>AI业务价值报告</h3></div><span>后端真实返回</span></div>
              <div v-if="businessReport.decisionSummary" class="business-summary"><span>决策摘要</span><p>{{ businessReport.decisionSummary }}</p></div>
              <div class="business-report-grid">
                <article v-if="businessReport.importantFindings.length"><h4>重要发现</h4><ul><li v-for="item in businessReport.importantFindings" :key="item">{{ item }}</li></ul></article>
                <article v-if="businessReport.businessOpportunities.length"><h4>业务机会</h4><ul><li v-for="item in businessReport.businessOpportunities" :key="item">{{ item }}</li></ul></article>
                <article v-if="businessReport.risks.length"><h4>风险提示</h4><ul><li v-for="item in businessReport.risks" :key="item">{{ item }}</li></ul></article>
                <article v-if="businessReport.recommendedActions.length"><h4>推荐行动</h4><ul><li v-for="item in businessReport.recommendedActions" :key="item">{{ item }}</li></ul></article>
              </div>
              <div v-if="businessReport.expectedValue" class="business-summary"><span>预期价值</span><p>{{ businessReport.expectedValue }}</p></div>
            </details>

            <details v-if="deliverables" class="deliverables-report compact-details" aria-label="研究产物"><summary>{{ deliverables.title }}</summary>
              <div class="business-report-heading"><div><p class="section-kicker">BUSINESS DELIVERABLE</p><h3>{{ deliverables.title }}</h3></div><span>由本次分析整理</span></div>
              <div class="deliverable-grid"><article v-for="entry in deliverables.entries" :key="entry[0]"><h4>{{ entry[0] }}</h4><template v-if="Array.isArray(entry[1])"><ul><li v-for="item in entry[1]" :key="item">{{ item }}</li></ul></template><p v-else>{{ entry[1] || '文档未说明' }}</p></article></div>
            </details>

            <details v-if="actionCenter" class="action-center compact-details" aria-label="下一步行动"><summary>下一步行动</summary>
              <div class="business-report-heading"><div><p class="section-kicker">ACTION CENTER</p><h3>下一步建议</h3></div><span>可继续验证</span></div>
              <div class="action-center-grid"><article><h4>立即行动</h4><ul><li v-for="item in actionCenter.nextActions" :key="item">{{ item }}</li></ul></article><article><h4>需要确认</h4><ul><li v-for="item in actionCenter.questionsToVerify" :key="item">{{ item }}</li></ul></article><article><h4>推荐任务</h4><ul><li v-for="item in actionCenter.recommendedTasks" :key="item">{{ item }}</li></ul></article></div>
            </details>

            <details class="simulation-panel compact-details" aria-label="模拟业务交流"><summary>模拟交流问题</summary>
              <div class="business-report-heading"><div><p class="section-kicker">BUSINESS SIMULATION</p><h3>模拟业务交流</h3></div><button type="button" class="outline-button" @click="showSimulation = !showSimulation">{{ showSimulation ? '收起问题' : '查看问题 TOP 5' }}</button></div>
              <p>基于当前 AI 员工角色整理业务交流时可用于人工准备的问题，不代表已获取客户或市场事实。</p>
              <ol v-if="showSimulation" class="simulation-list"><li v-for="item in simulationPrompts" :key="item">{{ item }}</li></ol>
            </details>

            <section v-if="decisionReport" class="decision-report" aria-label="AI决策支持报告">
              <div class="decision-report-heading">
                <div><p class="section-kicker">DECISION CONCLUSION</p><h3>AI决策结论</h3></div>
                <span>后端真实返回</span>
              </div>
              <div v-if="decisionReport.summary" class="decision-summary">
                <span>决策摘要</span><p>{{ decisionReport.summary }}</p>
              </div>
              <div class="decision-report-grid">
                <article v-if="decisionReport.keyPoints.length" class="decision-report-card">
                  <h4>关键要点</h4><ul><li v-for="item in decisionReport.keyPoints" :key="item">{{ item }}</li></ul>
                </article>
                <article v-if="decisionReport.risks.length" class="decision-report-card risk-card">
                  <h4>风险提示</h4><ul><li v-for="item in decisionReport.risks" :key="item">{{ item }}</li></ul>
                </article>
                <article v-if="decisionReport.recommendations.length" class="decision-report-card recommendation-card">
                  <h4>建议行动</h4><ul><li v-for="item in decisionReport.recommendations" :key="item">{{ item }}</li></ul>
                </article>
              </div>
              <div v-if="decisionReport.businessValue" class="business-value">
                <span>业务决策价值</span><p>{{ decisionReport.businessValue }}</p>
              </div>
            </section>

            <details class="analysis-details compact-details"><summary>查看完整分析</summary>
            <div class="paper-title-row">
              <div>
                <span class="result-label">文档标题</span>
                <h3>{{ analysisData.title || agentDecision?.documentType || "文档未说明" }}</h3>
              </div>
              <span class="status-pill">{{ result.task_type || "Agent 分析" }}</span>
            </div>

            <div v-if="analysisEntries.length" class="analysis-grid">
              <article v-for="entry in analysisEntries" :key="entry.key" class="analysis-card">
                <h3>{{ entry.label }}</h3>
                <template v-if="Array.isArray(entry.value)">
                  <ul class="finding-list">
                    <li v-for="item in entry.value" :key="item">{{ item }}</li>
                    <li v-if="!entry.value.length">文档未说明</li>
                  </ul>
                </template>
                <p v-else>{{ entry.value || "文档未说明" }}</p>
              </article>
            </div>
            <p v-else class="report-empty">后端未返回可展示的结构化报告字段。</p>
            </details>

            <details v-if="evidenceSources.length" class="evidence-section compact-details" aria-label="证据来源"><summary>引用来源</summary>
              <div><p class="section-kicker">EXPLAINABILITY</p><h3>证据来源</h3></div>
              <p>当前 MVP 提供文档章节级提示，尚未实现精确页码与段落定位。</p>
              <ul><li v-for="item in evidenceSources" :key="item.field"><b>{{ formatResultKey(item.field) }}</b><span>{{ item.source_section }}</span></li></ul>
            </details>

            <details v-if="evidenceCards.length" class="evidence-cards compact-details" aria-label="关键结论证据卡"><summary>关键结论依据</summary>
              <div><p class="section-kicker">EVIDENCE CARDS</p><h3>关键结论与依据</h3></div>
              <article v-for="item in evidenceCards" :key="item.finding"><p>{{ item.finding }}</p><div><span>📌 依据：{{ item.source }}</span><b>可信程度：{{ item.support_level === 'high' ? '高' : '中' }}</b></div></article>
            </details>

            <details v-if="qualityCheck" class="quality-check advanced-details" aria-label="高级技术信息">
              <summary>高级技术信息 · 结构化质量检查</summary>
              <div><p class="section-kicker">TECHNICAL INFORMATION</p><h3>技术信息</h3></div>
              <p><b>结构化结果完整度：</b>{{ qualityCheck.completeness ? "完整" : "存在待补充信息" }}</p>
              <p><b>规则质量评分：</b>{{ qualityCheck.score }}/100</p>
              <p v-if="qualityCheck.missing_information?.length"><b>待补充：</b>{{ qualityCheck.missing_information.join("、") }}</p>
            </details>
          </div>
        </section>
      </section>

      <section class="chat-panel">
        <div class="chat-header">
          <div><p class="section-kicker">FOLLOW-UP</p><h2>继续追问当前文档</h2></div>
          <span v-if="result" class="context-note">已连接当前文档</span>
        </div>

        <div v-if="!result" class="chat-empty">完成文档分析后，即可在这里继续对话。</div>
        <div v-else class="messages" aria-live="polite">
          <div v-for="(message, index) in chatMessages" :key="index" class="message-row" :class="message.role">
            <span class="message-avatar">{{ message.role === "user" ? "你" : "AI" }}</span><p>{{ message.content }}</p>
          </div>
          <div v-if="asking" class="message-row assistant thinking-message"><span class="message-avatar">AI</span><p><span class="typing-dot"></span><span class="typing-dot"></span><span class="typing-dot"></span></p></div>
        </div>

        <div class="chat-composer" :class="{ disabled: !result }">
          <input v-model="question" :disabled="!result || asking" placeholder="例如：这份文档有哪些实施风险？" @keyup.enter="askQuestion" />
          <button :disabled="!result || !question.trim() || asking" @click="askQuestion">{{ asking ? "思考中" : "发送" }} <span>→</span></button>
        </div>
      </section>
      </div>
      <section v-if="activeWorkspaceView === 'mission-center' && selectedAIMission?.source_materials?.length" class="mission-source-material"><p class="section-kicker">SOURCE MATERIAL</p><h3>Customer-provided input files</h3><article v-for="item in selectedAIMission.source_materials" :key="item.file_id"><b>{{ item.filename }}</b><small>{{ item.file_type }} · {{ item.classification }} · 不作为 RAG Evidence</small></article></section>
      <section v-if="activeWorkspaceView === 'mission-center' && selectedAIMission?.control" class="mission-control-surface" aria-label="Mission control"><header><div><p class="section-kicker">MISSION CONTROL</p><h3>{{ selectedAIMission.control.status === 'PAUSED' ? 'Mission is waiting' : selectedAIMission.control.status === 'FAILED' ? 'Mission needs attention' : 'Mission is active' }}</h3><p>{{ selectedAIMission.control.status === 'PAUSED' ? 'Work is safely paused. An authorized Workspace member can continue when ready.' : selectedAIMission.control.status === 'FAILED' ? 'A bounded recovery can prepare this mission for human review.' : 'You can pause this mission at any time without bypassing approval or review.' }}</p></div><small>{{ selectedAIMission.control.next_action }}</small></header><footer><button v-if="selectedAIMission.control.status !== 'PAUSED' && !['COMPLETED','REJECTED','FAILED'].includes(selectedAIMission.control.status)" class="outline-button" type="button" :disabled="aiMissionLoading" @click="updateMissionControl('pause')">Pause mission</button><button v-if="selectedAIMission.control.status === 'PAUSED'" class="primary-card-action" type="button" :disabled="aiMissionLoading" @click="updateMissionControl('resume')">Continue mission</button><button v-if="selectedAIMission.control.status === 'FAILED' && selectedAIMission.control.recovery_count < selectedAIMission.control.max_recoveries" class="primary-card-action" type="button" :disabled="aiMissionLoading" @click="updateMissionControl('recover')">Prepare recovery review</button><small v-if="selectedAIMission.control.status === 'FAILED'">{{ selectedAIMission.control.recovery_count }} of {{ selectedAIMission.control.max_recoveries }} recovery reviews used</small></footer></section>
      <section v-if="activeWorkspaceView === 'mission-center' && selectedAIMission?.workspace_context" class="mission-context-surface" aria-label="Authorized Mission Context"><p class="section-kicker">AUTHORIZED CONTEXT</p><h3>What AI Worker can use for this Mission</h3><article><b>{{ selectedAIMission.workspace_context.workspace.name }}</b><small>{{ selectedAIMission.workspace_context.workspace.member_count }} Workspace members · {{ selectedAIMission.workspace_context.knowledge.traceable_evidence_refs.length }} traceable Evidence reference(s)</small><p>Approved knowledge assets: {{ selectedAIMission.workspace_context.knowledge.approved_assets }} · Approved decisions: {{ selectedAIMission.workspace_context.knowledge.approved_decisions }} · {{ selectedAIMission.workspace_context.artifacts?.length || 0 }} approved delivery {{ selectedAIMission.workspace_context.artifacts?.length === 1 ? 'summary' : 'summaries' }} considered · Research Memory is limited to this authorized Workspace.</p></article></section>
      <section v-if="activeWorkspaceView === 'mission-center' && selectedAIMission?.workspace_context?.memory?.explainability" class="context-retrieval-surface" aria-label="Context selection"><header><div><p class="section-kicker">CONTEXT SELECTION</p><h3>Why this context is available</h3><p>AI Worker uses only relevant records already authorized for this Mission.</p></div><small>{{ selectedAIMission.workspace_context.memory.explainability.candidate_counts.authorized_memory }} memory candidate{{ selectedAIMission.workspace_context.memory.explainability.candidate_counts.authorized_memory === 1 ? '' : 's' }} · {{ selectedAIMission.workspace_context.memory.explainability.candidate_counts.approved_artifacts }} approved delivery candidate{{ selectedAIMission.workspace_context.memory.explainability.candidate_counts.approved_artifacts === 1 ? '' : 's' }}</small></header><ol><li v-for="item in selectedAIMission.workspace_context.memory.explainability.selected_context" :key="item.kind + item.title"><b>{{ item.title }}</b><p>{{ item.reason }}</p><small>{{ item.kind }} · context value {{ item.score }}</small></li></ol></section>
      <section v-if="activeWorkspaceView === 'mission-center' && selectedAIMission?.activity_timeline" class="ai-activity-surface" aria-label="AI Activity Timeline"><header><div><p class="section-kicker">AI ACTIVITY</p><h3>{{ selectedAIMission.activity_timeline.current_phase }}</h3><p>{{ selectedAIMission.activity_timeline.current_summary }}</p></div><small>{{ selectedAIMission.activity_timeline.next_action }}</small></header><ol><li v-for="item in selectedAIMission.activity_timeline.activities" :key="item.created_at + item.summary" :class="item.status.toLowerCase()"><span></span><div><b>{{ item.phase }}</b><p>{{ item.summary }}</p></div><small v-if="item.evidence_count">{{ item.evidence_count }} Evidence reference{{ item.evidence_count === 1 ? '' : 's' }}</small></li></ol></section>
      <section v-if="activeWorkspaceView === 'mission-center' && selectedAIMission?.worker_runtime?.team_plan" class="ai-team-plan-surface" aria-label="AI Worker plan"><header><div><p class="section-kicker">AI WORKER PLAN</p><h3>Skills selected for this Mission</h3><p>{{ selectedAIMission.worker_runtime.team_plan.boundary }}</p></div><small>{{ selectedAIMission.worker_runtime.team_plan.context_basis.authorized_memory_records }} memory record{{ selectedAIMission.worker_runtime.team_plan.context_basis.authorized_memory_records === 1 ? '' : 's' }} · {{ selectedAIMission.worker_runtime.team_plan.context_basis.traceable_evidence_references }} Evidence reference{{ selectedAIMission.worker_runtime.team_plan.context_basis.traceable_evidence_references === 1 ? '' : 's' }} · {{ selectedAIMission.worker_runtime.team_plan.context_basis.approved_artifact_summaries }} approved delivery {{ selectedAIMission.worker_runtime.team_plan.context_basis.approved_artifact_summaries === 1 ? 'summary' : 'summaries' }}</small></header><ol><li v-for="item in selectedAIMission.worker_runtime.team_plan.steps" :key="item.skill_id"><b>{{ item.name }}</b><p>{{ item.plan_reason }}</p><small>{{ item.status }}</small></li></ol><p v-for="item in selectedAIMission.worker_runtime.team_plan.deferred" :key="item.skill_id" class="team-plan-deferred"><b>{{ item.skill_id }} later</b> · {{ item.reason }}</p></section>
      <section v-if="activeWorkspaceView === 'mission-center' && selectedAIMission?.worker_runtime?.research_insight" class="research-insight-panel" aria-label="Research Insight">
        <header><div><p class="section-kicker">RESEARCH INSIGHT</p><h3>Evidence-bounded research strategy</h3><p>{{ selectedAIMission.worker_runtime.research_insight.strategy.boundary }}</p></div><span>{{ selectedAIMission.worker_runtime.research_insight.gap_analysis.status }}</span></header>
        <section class="research-insight-grid"><article><b>Research questions</b><ul><li v-for="item in selectedAIMission.worker_runtime.research_insight.strategy.research_questions" :key="item">{{ item }}</li></ul></article><article><b>Knowledge map</b><p>{{ selectedAIMission.worker_runtime.research_insight.strategy.knowledge_areas.join(' · ') }}</p><small>{{ selectedAIMission.worker_runtime.research_insight.strategy.evidence_count }} traceable Evidence reference(s) in scope.</small></article><article><b>Research gap</b><p v-for="item in selectedAIMission.worker_runtime.research_insight.gap_analysis.potential_gaps" :key="item.statement">{{ item.statement }}</p><p v-if="!selectedAIMission.worker_runtime.research_insight.gap_analysis.potential_gaps.length">No evidence-backed gap can be identified yet.</p></article><article><b>Innovation opportunities</b><p v-for="item in selectedAIMission.worker_runtime.research_insight.innovation_proposals" :key="item.opportunity">{{ item.opportunity }}</p><small v-if="!selectedAIMission.worker_runtime.research_insight.innovation_proposals.length">Evidence is required before proposing a reviewable validation opportunity.</small></article></section>
      </section>
      <section v-if="activeWorkspaceView === 'mission-center' && selectedAIMission?.worker_runtime?.autonomous_progress" class="ai-progress-panel" aria-label="AI Progress Timeline">
        <header><div><p class="section-kicker">AI PROGRESS</p><h3>AI Worker progress</h3><p>Only completed, reviewable workflow stages are shown. Internal reasoning is never displayed.</p></div></header>
        <ol><li v-for="item in selectedAIMission.worker_runtime.autonomous_progress" :key="item.label" :class="item.status.toLowerCase()"><span></span><b>{{ item.label }}</b><small>{{ item.status === 'COMPLETE' ? 'Completed' : item.status === 'ACTIVE' ? 'In progress' : 'Pending' }}</small></li></ol>
      </section>
      <section v-if="activeWorkspaceView === 'mission-center' && selectedAIMission?.worker_runtime?.mission_intelligence" class="mission-intelligence-panel" aria-label="Mission Intelligence">
        <header><div><p class="section-kicker">MISSION INTELLIGENCE</p><h3>Mission understanding</h3><p>{{ selectedAIMission.worker_runtime.mission_intelligence.understanding.goal_summary }}</p></div><span>{{ selectedAIMission.worker_runtime.mission_intelligence.quality.quality }}</span></header>
        <div class="mission-intelligence-grid"><article><b>Current phase</b><strong>{{ selectedAIMission.worker_runtime.mission_intelligence.current_phase }}</strong><small>{{ selectedAIMission.worker_runtime.mission_intelligence.quality.confidence }}</small></article><article><b>Completed tasks</b><strong>{{ selectedAIMission.worker_runtime.mission_intelligence.completed_tasks.length }}</strong><small>Only completed, user-reviewable tasks are counted.</small></article><article><b>Remaining tasks</b><ul><li v-for="task in selectedAIMission.worker_runtime.mission_intelligence.pending_tasks" :key="task.task_id">{{ task.required_skill }} · {{ task.status }}</li><li v-if="!selectedAIMission.worker_runtime.mission_intelligence.pending_tasks.length">No remaining task is available.</li></ul></article><article><b>Quality status</b><strong>{{ selectedAIMission.worker_runtime.mission_intelligence.quality.quality }}</strong><small>{{ selectedAIMission.worker_runtime.mission_intelligence.quality.next_action }}</small></article></div>
      </section>
    </main>
    <section v-else class="login-shell" aria-label="ResearchOS sign in">
      <div class="login-ambient" aria-hidden="true"></div>
      <form v-if="authMode === 'login'" class="login-card" @submit.prevent="loginToWorkspace">
        <div class="login-brand"><span class="brand-orb" aria-hidden="true">R</span><div><b>ResearchOS</b><small>Enterprise AI Workspace</small></div></div>
        <p class="section-kicker">WORKSPACE AUTHENTICATION</p>
        <h1>Sign in to your Workspace</h1>
        <p>ResearchOS loads Mission, Evidence, delivery and review data only after your Workspace identity is verified.</p>
        <label>Email<input v-model="loginForm.email" type="email" autocomplete="email" placeholder="you@organization.com" /></label>
        <label>Password<input v-model="loginForm.password" type="password" autocomplete="current-password" placeholder="Enter your password" /></label>
        <p v-if="loginError" class="login-error">{{ loginError }}</p>
        <button class="primary-card-action" type="submit" :disabled="loginLoading">{{ loginLoading ? 'Signing in…' : 'Sign in to Workspace' }}</button>
        <div class="auth-entry-actions"><button class="text-button" type="button" @click="authMode = 'register'; loginError = ''">Create account</button><button class="outline-button" type="button" :disabled="demoLoading" @click="startDemoSession">{{ demoLoading ? 'Starting demo…' : 'Try Demo' }}</button></div>
        <small class="login-boundary">Your Session is stored locally as an opaque token. Workspace access and role checks remain enforced by the API.</small>
      </form>
      <form v-else class="login-card register-card" @submit.prevent="registerWorkspace">
        <div class="login-brand"><span class="brand-orb" aria-hidden="true">R</span><div><b>ResearchOS</b><small>Enterprise AI Workspace</small></div></div>
        <p class="section-kicker">CREATE WORKSPACE</p>
        <h1>Create your AI Workspace</h1>
        <p>Create a private Workspace with you as its Owner. Roles and access controls remain enforced by the API.</p>
        <label>Name<input v-model="registrationForm.name" autocomplete="name" placeholder="Your name" /></label>
        <label>Email<input v-model="registrationForm.email" type="email" autocomplete="email" placeholder="you@organization.com" /></label>
        <label>Password<input v-model="registrationForm.password" type="password" autocomplete="new-password" minlength="12" placeholder="At least 12 characters" /></label>
        <label>Workspace name<input v-model="registrationForm.workspace_name" autocomplete="organization" placeholder="Innovation Research" /></label>
        <p v-if="loginError" class="login-error">{{ loginError }}</p>
        <button class="primary-card-action" type="submit" :disabled="loginLoading">{{ loginLoading ? 'Creating Workspace…' : 'Create Workspace' }}</button>
        <div class="auth-entry-actions"><button class="text-button" type="button" @click="authMode = 'login'; loginError = ''">Back to login</button><button class="outline-button" type="button" :disabled="demoLoading" @click="startDemoSession">{{ demoLoading ? 'Starting demo…' : 'Try Demo' }}</button></div>
      </form>
    </section>
  `,
}).mount("#app");
