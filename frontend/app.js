const { computed, createApp, ref } = Vue;

const API_BASE_URL = ["localhost", "127.0.0.1"].includes(window.location.hostname)
  ? "http://127.0.0.1:8000"
  : "https://ai-literature.onrender.com";
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
    const activeWorkspaceView = ref("demo");
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
    const ragHistory = ref([]);
    const ragHistoryLoading = ref(false);
    const ragSelectedSource = ref(null);
    const ragReportType = ref("literature_review");
    const ragReportResult = ref(null);
    const ragReportSources = ref([]);
    const ragReportQuality = ref(null);
    const ragReportTrace = ref(null);
    const ragReportEvaluation = ref(null);
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
    const researchOsGoal = ref("分析低碳建筑材料未来研究方向，并给出可验证的创新机会和项目成果路径。");
    const researchOsSelectedAgents = ref(["literature", "knowledge", "trend", "innovation", "project", "report"]);
    const researchOsTaskResult = ref(null);
    const researchOsTaskLoading = ref(false);
    const researchOsError = ref("");
    const researchBi = ref(null);
    const researchBiLoading = ref(false);
    const researchProjects = ref([]);
    const projectLoading = ref(false);
    const projectError = ref("");
    const projectMatching = ref(false);
    const projectMatchResult = ref(null);
    const projectForm = ref({ name: "", enterprise_requirement: "", research_goal: "", technology_route: "", paper_plan: "", patent_plan: "", outcome_management: "", status: "planning" });
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
      return [
        { agent: "Research Master", action: "理解企业需求与研究目标", status, label },
        { agent: "Knowledge Agent", action: "检索实验室科研资料", status, label },
        { agent: "Innovation Agent", action: "分析创新机会与验证方向", status, label },
        { agent: "Project Agent", action: "组织项目方案与成果路径", status, label },
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
      if (view === "projects") await loadResearchProjects();
      if (view === "bi") await loadResearchBi();
      if (view === "evidence") await loadEvidenceCenter();
      if (view === "lab-profile") await loadResearchBi();
      if (view === "system") await loadSystemStatus();
      void loadResearchOverview();
    }

    async function loadResearchOsData() {
      try {
        const [overviewResponse, agentsResponse] = await Promise.all([
          fetchWithTimeout(`${API_BASE_URL}/researchos/overview`, { method: "GET" }),
          fetchWithTimeout(`${API_BASE_URL}/researchos/agents`, { method: "GET" }),
        ]);
        researchOsOverview.value = await readResponse(overviewResponse);
        const agentData = await readResponse(agentsResponse);
        researchOsAgents.value = Array.isArray(agentData.agents) ? agentData.agents : [];
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
          }),
        });
        researchOsTaskResult.value = await readResponse(response);
        recordActivity("Agent 执行完成", "Research Master 已完成科研任务编排与专项分析输出。");
      } catch (error) {
        researchOsError.value = error.message || "科研任务执行失败，请稍后重试。";
      } finally {
        researchOsTaskLoading.value = false;
      }
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
      demoStarted.value = true;
      activeWorkspaceView.value = "demo";
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
        researchProjects.value = [await readResponse(response), ...researchProjects.value];
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
        recordActivity("Agent 执行完成", `Project Agent 已完成「${project.name}」的企业需求匹配。`);
      } catch (error) {
        projectError.value = error.message || "需求匹配执行失败。";
      } finally {
        projectMatching.value = false;
      }
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

    async function readResponse(response) {
      let data;
      try {
        data = await response.json();
      } catch {
        throw new Error("服务器返回异常，请稍后重试。");
      }
      if (!response.ok) {
        if (typeof data.detail === "string") throw new Error(data.detail);
        if (response.status === 503) throw new Error("后端服务暂时不可用，请稍后重试。");
        if (response.status >= 500) throw new Error("服务处理失败，请稍后重试。");
        throw new Error("请求参数不正确，请检查输入后重试。");
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
        return await fetch(url, { ...options, signal: controller.signal });
      } catch (error) {
        if (timedOut) throw new Error("请求超时，请稍后重试或上传篇幅更短的文档。");
        if (error instanceof TypeError) {
          throw new Error("无法连接后端服务，请确认后端已启动后重试。");
        }
        throw error;
      } finally {
        window.clearTimeout(timeout);
      }
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

    void loadResearchOverview();
    void loadResearchOsData();
    void loadResearchBi();

    return {
      agentDecision,
      agentTrace,
      agentWorkflow,
      activeWorkspaceView,
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
      ragReportResult,
      ragReportSources,
      ragReportTasks: RESEARCH_REPORT_TASKS,
      ragReportType,
      ragSelectedPaperIds,
      ragSelectedSource,
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
      researchOsSections,
      agentTimeline,
      aiActivityStream,
      agentTeamCards,
      evidenceCenterItems,
      evidenceError,
      evidenceLoading,
      systemStatus,
      systemStatusLoading,
      systemStatusError,
      activityLogs,
      demoKnowledgeInitialized,
      visibleDemoKnowledgeAssets,
      researchOsSelectedAgents,
      researchOsTaskLoading,
      researchOsTaskResult,
      researchBi,
      researchBiLoading,
      researchProjects,
      projectError,
      projectForm,
      projectLoading,
      projectMatchResult,
      projectMatching,
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
      loadResearchBi,
      loadResearchProjects,
      runProjectMatch,
      generateLabProfile,
      loadEvidenceCenter,
      loadSystemStatus,
      initializeDemoKnowledge,
      runResearchOsTask,
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
    <main class="app-shell">
      <header class="workspace-header">
        <nav class="top-navigation" aria-label="主导航">
          <button class="brand-button" type="button" @click="openWorkspaceView('dashboard')"><span class="brand-orb">✦</span><span>ResearchOS</span></button>
          <div class="top-navigation-links"><button type="button" :class="{ active: activeWorkspaceView === 'demo' }" @click="startDemoMode">现场演示</button><button type="button" :class="{ active: activeWorkspaceView === 'tasks' || activeWorkspaceView === 'assistant' }" @click="openWorkspaceView('tasks')">AI助手</button><button type="button" :class="{ active: activeWorkspaceView === 'knowledge' }" @click="openWorkspaceView('knowledge')">知识空间</button><button type="button" :class="{ active: activeWorkspaceView === 'timeline' || activeWorkspaceView === 'agents' }" @click="openWorkspaceView('agents')">Agent团队</button><button type="button" :class="{ active: activeWorkspaceView === 'projects' || activeWorkspaceView === 'delivery' }" @click="openWorkspaceView('projects')">科研项目</button><button type="button" :class="{ active: activeWorkspaceView === 'fde-report' || activeWorkspaceView === 'evidence' || activeWorkspaceView === 'customer-value' }" @click="openWorkspaceView('fde-report')">解决方案</button><button type="button" :class="{ active: activeWorkspaceView === 'bi' || activeWorkspaceView === 'lab-profile' || activeWorkspaceView === 'insights' }" @click="openWorkspaceView('bi')">科研洞察</button><button type="button" :class="{ active: activeWorkspaceView === 'system' }" @click="openWorkspaceView('system')">系统状态</button></div>
          <span class="top-navigation-status"><i></i> ResearchOS v1.0</span>
        </nav>
        <div v-if="activeWorkspaceView === 'dashboard'" class="minimal-hero researchos-hero">
          <p class="section-kicker">AI RESEARCH CONSULTANT</p><h1>ResearchOS 科研顾问</h1>
          <p>从企业需求出发，连接实验室知识资产、技术路线与科研成果规划。</p>
          <div class="hero-tags" aria-label="核心价值"><span>需求理解</span><span>技术路线</span><span>成果规划</span></div>
          <div class="researchos-hero-actions"><button type="button" class="primary-card-action" @click="applyFdeDeliveryDemo">体验低碳材料企业合作案例</button><button type="button" class="outline-button" @click="openWorkspaceView('tasks')">探索研究方向</button></div>
        </div>
      </header>

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

      <section v-if="activeWorkspaceView === 'dashboard'" class="researchos-dashboard" aria-label="ResearchOS 科研驾驶舱">
        <div class="dashboard-heading"><div><p class="section-kicker">RESEARCH COMMAND CENTER</p><h2>科研驾驶舱</h2><p>将团队已上传的科研资料转化为可复核的知识、洞察和行动建议。</p></div><span>某高校建筑材料实验室 · 示例工作空间</span></div>
        <section class="advisor-entry"><div><p class="section-kicker">WHO IS USING RESEARCHOS</p><h3>选择你的角色视角</h3><p>{{ advisorRoles.find((item) => item.id === advisorAudience)?.description }}</p></div><div class="advisor-role-options"><button v-for="item in advisorRoles" :key="item.id" type="button" :class="{ active: advisorAudience === item.id }" @click="advisorAudience = item.id">{{ item.name }}</button></div></section>
        <section class="advisor-scenarios"><article><span>01</span><h3>企业需求分析</h3><p>从企业需求到实验室能力匹配、技术建议与成果路径。</p><button type="button" @click="selectAdvisorScenario('enterprise')">进入 FDE 交付</button></article><article><span>02</span><h3>研究方向探索</h3><p>从团队资料中归纳趋势、创新机会与验证任务。</p><button type="button" @click="selectAdvisorScenario('explore')">开始探索</button></article><article><span>03</span><h3>实验室知识管理</h3><p>统一管理论文、专利、实验报告和项目资料。</p><button type="button" @click="selectAdvisorScenario('knowledge')">管理资料</button></article></section>
        <div class="dashboard-stat-grid"><article><span>科研论文</span><strong>{{ researchOsOverview?.paper_count ?? libraryPapers.length }}</strong><small>当前已纳入知识空间</small></article><article><span>知识片段</span><strong>{{ researchOsOverview?.knowledge_chunk_count ?? knowledgeChunkTotal }}</strong><small>用于检索与证据引用</small></article><article><span>索引就绪</span><strong>{{ researchOsOverview?.ready_paper_count ?? readyPaperCount }}</strong><small>可参与多论文问答</small></article><article><span>研究报告</span><strong>{{ researchOverview?.analysis_count ?? 0 }}</strong><small>历史分析成果</small></article></div>
        <div class="researchos-dashboard-grid"><section class="dashboard-card"><p class="section-kicker">AI RESEARCH INSIGHT</p><h3>从资料到研究决策</h3><ol class="researchos-flow"><li>上传论文与科研资料</li><li>Research Master 理解目标并编排任务</li><li>专项 Agent 基于知识库检索证据</li><li>生成趋势、创新机会与成果规划建议</li></ol><button class="outline-button" type="button" @click="openWorkspaceView('knowledge')">管理科研知识库</button></section><section class="dashboard-card accent-card"><p class="section-kicker">FDE DELIVERY CASE</p><h3>低碳建筑材料企业需求</h3><p>企业需求 → 实验室匹配 → 技术路线 → 创新机会 → 项目规划 → 成果预测。</p><button class="primary-card-action" type="button" @click="applyFdeDeliveryDemo">启动完整 FDE 演示</button><small>实际结果必须由已上传资料和 Agent 调用生成。</small></section></div>
        <div class="researchos-dashboard-grid lifecycle-preview"><section class="dashboard-card"><p class="section-kicker">PROJECT LIFECYCLE</p><h3>科研项目生命周期</h3><div class="lifecycle-strip"><span>项目创建</span><i>→</i><span>研究目标</span><i>→</i><span>技术路线</span><i>→</i><span>论文 / 专利规划</span><i>→</i><span>成果管理</span></div><button class="outline-button" type="button" @click="openWorkspaceView('projects')">进入科研项目中心</button></section><section class="dashboard-card"><p class="section-kicker">RESEARCH BI</p><h3>科研资产与技术路线</h3><p>查看当前资料构成、知识片段、项目数与基于资料的趋势分析入口。</p><button class="outline-button" type="button" @click="openWorkspaceView('bi')">打开科研 BI 驾驶舱</button></section></div>
        <section class="lab-profile-card"><div><p class="section-kicker">LAB PROFILE</p><h3>实验室科研能力画像</h3><p>由 Knowledge Agent 根据已上传资料归纳研究方向、核心能力、成果线索与合作方向。</p></div><button class="outline-button" type="button" :disabled="labProfileLoading" @click="generateLabProfile">{{ labProfileLoading ? '生成中…' : '生成能力画像' }}</button><div v-if="labProfile" class="lab-profile-grid"><article><h4>研究方向</h4><ul><li v-for="item in labProfile.research_directions" :key="item">{{ item }}</li></ul></article><article><h4>核心能力</h4><ul><li v-for="item in labProfile.core_capabilities" :key="item">{{ item }}</li></ul></article><article><h4>成果线索</h4><ul><li v-for="item in labProfile.research_outputs" :key="item">{{ item }}</li></ul></article><article><h4>合作方向</h4><ul><li v-for="item in labProfile.collaboration_directions" :key="item">{{ item }}</li></ul></article></div><small v-if="labProfile">{{ labProfile.boundary_note }}</small></section>
        <p v-if="researchOsError" class="error-alert"><span>!</span>{{ researchOsError }}</p>
      </section>

      <section v-if="activeWorkspaceView === 'tasks'" class="researchos-task-center" aria-label="科研任务中心">
        <div class="dashboard-heading"><div><p class="section-kicker">RESEARCH TASK CENTER</p><h2>科研任务中心</h2><p>Research Master 会先理解目标，再调度所选专项 Agent，并依据团队资料生成可复核结果。</p></div><button class="outline-button" type="button" @click="openWorkspaceView('assistant')">单篇文献分析工作台</button></div>
        <p v-if="researchOsError" class="error-alert"><span>!</span>{{ researchOsError }}</p>
        <div class="researchos-task-layout"><section class="task-config-card"><label for="researchos-goal">研究需求</label><textarea id="researchos-goal" v-model="researchOsGoal" rows="6" placeholder="例如：分析低碳建筑材料未来研究方向"></textarea><div class="agent-select-heading"><span>选择参与任务的 Agent</span><button class="text-button" type="button" @click="applyResearchOsDemo">填充比赛案例</button></div><div class="researchos-agent-selector"><button v-for="agent in researchOsAgents" :key="agent.id" type="button" :class="{ active: researchOsSelectedAgents.includes(agent.id) }" @click="toggleResearchOsAgent(agent.id)"><b>{{ agent.name_cn }}</b><small>{{ agent.description }}</small></button></div><button class="analyze-button" type="button" :disabled="researchOsTaskLoading" @click="runResearchOsTask"><span v-if="researchOsTaskLoading" class="spinner small-spinner"></span>{{ researchOsTaskLoading ? 'ResearchOS 正在协作…' : '启动多 Agent 科研任务' }}</button></section>
          <section class="researchos-result-card"><div v-if="researchOsTaskLoading" class="loading-state"><span class="spinner"></span><h3>Research Master 正在编排任务</h3><ol class="loading-workflow"><li><i></i>理解科研目标</li><li><i></i>检索团队知识库</li><li><i></i>调度专项 Agent</li><li><i></i>生成科研决策报告</li></ol></div><div v-else-if="!researchOsTaskResult" class="empty-state"><div class="empty-illustration">✦</div><h3>等待科研任务</h3><p>上传相关论文后，输入一个研究目标，获得基于团队知识资产的科研辅助结果。</p></div><div v-else class="researchos-result"><p class="section-kicker">RESEARCH DECISION REPORT</p><h3>科研决策结论</h3><p class="researchos-executive-summary">{{ researchOsTaskResult.executive_summary }}</p><section class="agent-run-board"><h4>Agent 执行状态</h4><article v-for="run in researchOsTaskResult.agent_runs || []" :key="run.agent"><b>✓</b><div><strong>{{ run.agent }}</strong><p>{{ run.message }}</p></div><span>{{ run.status === 'completed' ? '已完成' : run.status }}</span></article></section><details open class="master-plan-card"><summary>Research Master 执行流程</summary><ol><li v-for="step in researchOsTaskResult.master_plan?.workflow_steps || []" :key="step.step"><b>{{ step.step }}</b><div><strong>{{ step.action }}</strong><p>{{ step.agent }} · {{ step.purpose }}</p></div></li></ol></details><section v-for="section in researchOsSections" :key="section[0]" class="researchos-output-section"><h4>{{ section[0] }}</h4><dl><template v-for="(value, key) in section[1]" :key="key"><dt>{{ key }}</dt><dd v-if="Array.isArray(value)"><ul><li v-for="item in value" :key="item">{{ item }}</li></ul></dd><dd v-else>{{ value }}</dd></template></dl></section><details v-if="researchOsTaskResult.sources?.length" class="master-plan-card"><summary>证据来源（{{ researchOsTaskResult.sources.length }}）</summary><article v-for="source in researchOsTaskResult.sources" :key="source.paper_id + source.section"><b>{{ source.paper_title }}</b><span>{{ source.section }} · {{ source.score }}</span><p>{{ source.content }}</p></article></details><p class="trace-boundary">{{ researchOsTaskResult.boundary_note }}</p></div></section></div>
      </section>

      <section v-if="activeWorkspaceView === 'projects'" class="researchos-projects" aria-label="科研项目中心"><div class="dashboard-heading"><div><p class="section-kicker">RESEARCH PROJECT LIFECYCLE</p><h2>科研项目中心</h2><p>把企业需求、研究目标、技术路线、论文专利规划和成果管理放在同一条项目生命周期中。</p></div></div><p v-if="projectError" class="error-alert"><span>!</span>{{ projectError }}</p><div class="project-workspace"><section class="task-config-card"><label>新建科研项目</label><input v-model="projectForm.name" placeholder="项目名称，例如：低碳建筑材料关键技术研发" /><textarea v-model="projectForm.enterprise_requirement" rows="4" placeholder="企业需求：例如开发绿色建筑材料并验证工程适用性"></textarea><textarea v-model="projectForm.research_goal" rows="3" placeholder="研究目标"></textarea><textarea v-model="projectForm.technology_route" rows="3" placeholder="技术路线（可后续完善）"></textarea><textarea v-model="projectForm.paper_plan" rows="2" placeholder="论文规划"></textarea><textarea v-model="projectForm.patent_plan" rows="2" placeholder="专利规划"></textarea><textarea v-model="projectForm.outcome_management" rows="2" placeholder="成果管理"></textarea><button class="analyze-button" type="button" :disabled="projectLoading" @click="createResearchProject">{{ projectLoading ? '保存中…' : '创建科研项目' }}</button></section><section class="project-list-panel"><div v-if="projectLoading && !researchProjects.length" class="loading-state"><span class="spinner"></span><p>正在读取项目…</p></div><div v-else-if="!researchProjects.length" class="empty-state"><div class="empty-illustration">◫</div><h3>暂无科研项目</h3><p>创建项目后，可用 Project Agent 评估企业需求与实验室能力匹配。</p></div><article v-for="project in researchProjects" :key="project.id" class="project-card"><div><span>{{ project.status }}</span><time>{{ formatLibraryDate(project.updated_at) }}</time></div><h3>{{ project.name }}</h3><p>{{ project.research_goal || project.enterprise_requirement || '尚未补充项目目标。' }}</p><footer><span>论文：{{ project.paper_plan ? '已规划' : '待规划' }} · 专利：{{ project.patent_plan ? '已规划' : '待规划' }}</span><button class="primary-card-action" type="button" :disabled="projectMatching" @click="runProjectMatch(project)">{{ projectMatching ? '匹配中…' : '需求匹配' }}</button></footer></article></section></div><section v-if="projectMatchResult" class="project-match-result"><p class="section-kicker">PROJECT AGENT RESULT</p><h3>{{ projectMatchResult.projectName }} · 横向需求匹配</h3><div class="project-match-grid"><article><h4>实验室能力匹配</h4><ul><li v-for="item in projectMatchResult.lab_capability_match" :key="item">{{ item }}</li></ul></article><article><h4>技术方案建议</h4><ul><li v-for="item in projectMatchResult.technical_solution_suggestions" :key="item">{{ item }}</li></ul></article><article><h4>预期成果规划</h4><dl><template v-for="(value,key) in projectMatchResult.expected_outcome_plan" :key="key"><dt>{{ key }}</dt><dd>{{ Array.isArray(value) ? value.join('、') : value }}</dd></template></dl></article><article><h4>风险与待确认问题</h4><ul><li v-for="item in projectMatchResult.risks_and_questions" :key="item">{{ item }}</li></ul></article></div><section class="agent-run-board"><h4>Project Agent 执行过程</h4><article v-for="trace in projectMatchResult.agent_trace" :key="trace.agent"><b>✓</b><div><strong>{{ trace.agent }}</strong><p>{{ trace.message }}</p></div><span>已完成</span></article></section><p class="trace-boundary">{{ projectMatchResult.boundary_note }}</p></section></section>

      <section v-if="activeWorkspaceView === 'bi'" class="researchos-bi" aria-label="科研BI驾驶舱"><div class="dashboard-heading"><div><p class="section-kicker">RESEARCH BUSINESS INTELLIGENCE</p><h2>科研 BI 驾驶舱</h2><p>从团队已沉淀资料中查看科研资产、成果统计与技术路线状态。</p></div><button class="outline-button" type="button" :disabled="researchBiLoading" @click="loadResearchBi">{{ researchBiLoading ? '刷新中…' : '刷新数据' }}</button></div><p v-if="projectError" class="error-alert"><span>!</span>{{ projectError }}</p><div v-if="researchBi" class="bi-grid"><article><p>科研论文 / 资料</p><strong>{{ researchBi.research_assets?.papers || 0 }}</strong><span>已入库科研资产</span></article><article><p>知识片段</p><strong>{{ researchBi.research_assets?.knowledge_chunks || 0 }}</strong><span>可用于 Agent 检索</span></article><article><p>科研项目</p><strong>{{ researchBi.research_assets?.projects || 0 }}</strong><span>生命周期管理中</span></article></div><div v-if="researchBi" class="researchos-dashboard-grid"><section class="dashboard-card"><p class="section-kicker">ASSET DISTRIBUTION</p><h3>科研资料构成</h3><ul class="bi-list"><li v-for="item in researchBi.asset_distribution" :key="item.document_type"><span>{{ item.document_type }}</span><b>{{ item.count }}</b></li></ul><p v-if="!researchBi.asset_distribution?.length">暂无已入库资料。</p></section><section class="dashboard-card"><p class="section-kicker">TECHNOLOGY ROADMAP</p><h3>技术路线图</h3><ol class="researchos-flow"><li v-for="item in researchBi.technology_roadmap" :key="item">{{ item }}</li></ol></section><section class="dashboard-card"><p class="section-kicker">RESEARCH HOTSPOTS</p><h3>研究热点分析</h3><p>{{ researchBi.trend_boundary }}</p><ul class="bi-list"><li v-for="title in researchBi.latest_assets" :key="title"><span>{{ title }}</span></li></ul><button class="outline-button" type="button" @click="openWorkspaceView('tasks')">运行趋势分析任务</button></section></div></section>

      <section v-if="activeWorkspaceView === 'agents'" class="researchos-agents" aria-label="AI Agent中心"><div class="dashboard-heading"><div><p class="section-kicker">AI RESEARCH TEAM</p><h2>AI 科研团队</h2><p>每位 AI 成员承担清晰角色，共享团队知识库证据，在 Research Master 的编排下完成科研协作。</p></div><button class="outline-button" type="button" @click="openWorkspaceView('timeline')">查看工作流</button></div><div class="master-architecture team-member-grid"><article v-for="agent in agentTeamCards" :key="agent.id"><div class="team-member-avatar">{{ agent.name.slice(0, 1) }}</div><p>{{ agent.name }}</p><h3>{{ agent.name_cn }}</h3><span>{{ agent.description }}</span><small>{{ agent.purpose }}</small><footer>知识依据 · 协作输出</footer></article></div></section>

      <section v-if="activeWorkspaceView === 'knowledge'" class="library-workspace" aria-label="科研知识库">
        <div class="library-header"><div><p class="section-kicker">LAB KNOWLEDGE BASE</p><h2>科研知识库</h2><p>已保存并解析的团队科研资料，可直接进入 AI 助手或参与多论文检索。</p></div><div class="library-header-actions"><select v-model="libraryDocumentType" aria-label="科研资料类型"><option value="paper">论文</option><option value="patent">专利</option><option value="experiment_report">实验报告</option><option value="project_material">项目资料</option></select><label class="library-upload-button" :class="{ busy: libraryUploading }"><input ref="libraryFileInput" type="file" accept="application/pdf,.pdf" :disabled="libraryUploading" @change="uploadLibraryPaper" /><span>{{ libraryUploading ? '正在保存资料…' : '＋ 上传 PDF 资料' }}</span></label><button class="outline-button" type="button" :disabled="libraryLoading" @click="loadLibraryPapers">{{ libraryLoading ? '刷新中' : '刷新列表' }}</button></div></div>
        <div v-if="libraryPapers.length" class="library-toolbar"><label><span>⌕</span><input v-model="librarySearch" type="search" placeholder="搜索论文标题或文件名" /></label><select v-model="libraryStatusFilter" aria-label="按知识库状态筛选"><option value="all">全部状态</option><option value="ready">Ready</option><option value="indexed">Indexed</option><option value="parsed">Parsed</option><option value="failed">Failed</option></select><small>共 {{ filteredLibraryPapers.length }} / {{ libraryPapers.length }} 篇资料</small></div>
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
        <div class="library-header"><div><p class="section-kicker">RESEARCH INSIGHTS</p><h2>科研洞察</h2><p>Research Agent 会检索团队知识库中的相关片段，再基于引用证据回答问题。</p></div><div class="library-header-actions"><button class="outline-button" type="button" :disabled="libraryLoading" @click="loadLibraryPapers">{{ libraryLoading ? '刷新中' : '刷新论文范围' }}</button></div></div>
        <p v-if="ragError" class="error-alert" role="alert"><span>!</span>{{ ragError }}</p>
        <div v-if="!libraryPapers.length && !libraryLoading" class="library-empty-state"><div class="empty-illustration">⌕</div><h3>暂无可检索论文</h3><p>请先在“我的论文库”上传论文，并等待知识索引建立完成。</p></div>
        <div v-else class="rag-content"><section class="knowledge-status-strip" aria-label="当前知识库状态"><div><span>论文</span><strong>{{ libraryPapers.length }}</strong><small>篇资料</small></div><div><span>知识片段</span><strong>{{ knowledgeChunkTotal }}</strong><small>个可检索片段</small></div><div><span>已就绪</span><strong>{{ readyPaperCount }}</strong><small>篇论文</small></div></section><details class="rag-scope compact-details"><summary>选择论文范围</summary><div class="rag-paper-options"><label v-for="paper in libraryPapers" :key="paper.paper_id"><input v-model="ragSelectedPaperIds" type="checkbox" :value="paper.paper_id" :disabled="!['indexed', 'ready'].includes(paper.quality_status || paper.analysis_status)" /><span>{{ paper.title }}</span><em>{{ paper.quality_status || libraryStatusLabel(paper.analysis_status) }}</em></label></div></details>
          <section class="research-task-center"><div><p class="section-kicker">RESEARCH TASK CENTER</p><h3>研究任务中心</h3><p>选择任务后，Agent 会检索选定论文并生成结构化研究报告。</p></div><div class="report-task-options"><button v-for="item in ragReportTasks" :key="item.id" type="button" :class="{ active: ragReportType === item.id }" @click="ragReportType = item.id"><b>{{ item.name }}</b><small>{{ item.description }}</small></button></div><button class="outline-button" type="button" :disabled="ragReportLoading" @click="generateResearchReport">{{ ragReportLoading ? '正在生成研究报告…' : '生成结构化报告' }}</button><p v-if="ragReportError" class="error-alert" role="alert"><span>!</span>{{ ragReportError }}</p><div v-if="ragReportResult" class="rag-report-card"><div class="rag-answer-heading"><div><p class="section-kicker">STRUCTURED RESEARCH REPORT</p><h3>研究任务结果</h3></div><span>{{ ragReportQuality?.evidence_level || 'low' }} evidence</span></div><article v-for="(value, key) in ragReportResult" :key="key"><h4>{{ key }}</h4><p v-if="typeof value === 'string'">{{ value }}</p><ul v-else><li v-for="item in value" :key="item">{{ item }}</li></ul></article><footer v-if="ragReportEvaluation">检索质量：<b>{{ ragReportEvaluation.retrieval_quality }}</b> · {{ ragReportEvaluation.retrieval_count }} 条证据 · 最高分 {{ ragReportEvaluation.highest_score }}</footer></div></section>
          <div class="rag-question-form"><label for="rag-question">请输入科研知识问题</label><textarea id="rag-question" v-model="ragQuestion" rows="5" placeholder="例如：总结这些论文在研究方法上的差异，并说明各自的适用边界。"></textarea><button class="analyze-button" type="button" :disabled="ragLoading || !libraryPapers.length" @click="askResearchQuestion"><span v-if="ragLoading" class="spinner small-spinner"></span>{{ ragLoading ? 'Agent 正在检索论文证据…' : '开始知识问答' }}</button></div>
          <div v-if="ragLoading" class="loading-state rag-loading"><div class="process-heading"><span class="spinner"></span><div><h3>Research Agent 正在处理问题</h3><p>正在分析问题、改写检索 Query、检索相关论文、筛选证据并生成回答。</p></div></div><ol class="loading-workflow"><li><i></i>分析研究任务</li><li><i></i>检索相关论文</li><li><i></i>筛选与重排证据</li><li><i></i>生成可信回答</li></ol></div>
          <details v-if="ragAgentPlan && !ragLoading" class="rag-plan compact-details"><summary>AI 执行过程</summary><span>✓ 理解问题</span><span>✓ 检索论文</span><span>✓ 筛选证据</span><span>✓ 生成回答</span><p>{{ ragAgentPlan.instruction }}</p><small>优化检索 Query：{{ ragAgentPlan.retrieval_query }}</small></details>
          <details v-if="ragAgentTrace?.steps?.length" class="rag-trace compact-details" aria-label="AI执行过程"><summary>查看执行摘要</summary><ol><li v-for="(trace, index) in ragAgentTrace.steps" :key="trace.created_at + trace.step"><b>✓</b><div><strong>{{ index + 1 }}. {{ trace.step }}</strong><p>{{ trace.message }}</p></div></li></ol></details>
          <details v-if="ragRetrievalEvaluation" class="rag-evaluation compact-details" aria-label="检索效果"><summary>检索质量 · {{ ragRetrievalEvaluation.retrieval_quality }}</summary><dl><div><dt>检索证据</dt><dd>{{ ragRetrievalEvaluation.retrieval_count }} 条</dd></div><div><dt>平均分</dt><dd>{{ ragRetrievalEvaluation.average_score }}</dd></div><div><dt>最高分</dt><dd>{{ ragRetrievalEvaluation.highest_score }}</dd></div></dl><small>该评分反映检索匹配质量，不代表回答事实准确率。</small></details>
          <div v-if="ragAnswer" class="rag-answer-card"><div class="rag-answer-heading"><div><p class="section-kicker">EVIDENCE-GROUNDED ANSWER</p><h3>AI 回答</h3></div><span>检索匹配度：{{ ragConfidence }}</span></div><p>{{ ragAnswer }}</p><footer v-if="ragSourceQuality">证据等级：<b>{{ ragSourceQuality.evidence_level }}</b> · {{ ragSourceQuality.citation_count }} 条引用 · 平均分 {{ ragSourceQuality.average_score }}</footer></div>
          <div v-if="ragSources.length" class="rag-sources"><div class="result-section-heading"><div><p class="section-kicker">RETRIEVAL SOURCES</p><h3>引用论文片段</h3></div><span>{{ ragSources.length }} 条证据</span></div><article v-for="(source, index) in ragSources" :key="source.paper_id + '-' + index" class="rag-source-card" tabindex="0" @click="showRagSource(source)"><div><span class="evidence-number">{{ index + 1 }}</span><div><h4>{{ source.paper_title }}</h4><p>章节：{{ source.section }}</p></div><strong>{{ Number(source.score).toFixed(4) }}</strong></div><blockquote>{{ source.content }}</blockquote></article></div>
          <aside v-if="ragSelectedSource" class="rag-source-detail"><div class="library-detail-heading"><div><p class="section-kicker">SOURCE DETAIL</p><h3>{{ ragSelectedSource.paper_title }}</h3></div><button type="button" class="text-button" @click="ragSelectedSource = null">关闭</button></div><p><b>来源章节：</b>{{ ragSelectedSource.section }}</p><blockquote>{{ ragSelectedSource.content }}</blockquote><small>相似度：{{ Number(ragSelectedSource.score).toFixed(4) }}</small></aside>
          <section class="rag-history"><div class="result-section-heading"><div><p class="section-kicker">RAG HISTORY</p><h3>历史知识问答</h3></div><button class="text-button" type="button" @click="loadRagHistory">{{ ragHistoryLoading ? '加载中' : '刷新' }}</button></div><p v-if="!ragHistory.length" class="field-hint">暂无历史知识问答。</p><article v-for="record in ragHistory" :key="record.id"><div><b>{{ record.question }}</b><time>{{ formatLibraryDate(record.created_at) }}</time></div><p>{{ record.answer }}</p><button type="button" class="text-button" @click="restoreRagHistory(record)">查看引用</button></article></section>
        </div>
      </section>

      <section v-if="activeWorkspaceView === 'tasks' && researchOsTaskResult" class="value-agent-card task-value-entry"><div><p class="section-kicker">VALUE AGENT</p><h3>科研价值评估</h3><p>对当前研究方向的资料覆盖、创新机会和成果路径进行辅助判断。</p></div><button class="outline-button" type="button" :disabled="valueAssessmentLoading" @click="assessResearchValue">{{ valueAssessmentLoading ? '评估中…' : '运行 Value Agent' }}</button><div v-if="valueAssessment" class="value-agent-grid"><article v-for="item in [['研究热度',valueAssessment.research_heat],['创新潜力',valueAssessment.innovation_potential],['成果潜力',valueAssessment.outcome_potential]]" :key="item[0]"><h4>{{ item[0] }} <span :class="item[1].level">{{ item[1].level }}</span></h4><p>{{ item[1].explanation }}</p></article></div><p v-if="valueAssessment" class="trace-boundary">{{ valueAssessment.boundary_note }}</p></section>

      <section v-if="activeWorkspaceView === 'bi' && researchBi" class="bi-visual-board"><section><p class="section-kicker">RESEARCH HOTSPOT TREND</p><h3>热点趋势图</h3><div class="bar-chart"><div v-for="item in researchBi.asset_distribution" :key="item.document_type"><span :style="{ height: Math.max(12, item.count * 24) + 'px' }"></span><small>{{ item.document_type }}</small></div></div><p>柱状高度表示当前已入库资料类型数量，不代表外部领域热度。</p></section><section><p class="section-kicker">OUTCOME CONVERSION</p><h3>成果转化漏斗</h3><ol class="funnel-list"><li v-for="item in researchBi.outcome_funnel" :key="item.stage"><span>{{ item.stage }}</span><b>{{ item.count }}</b></li></ol></section><section><p class="section-kicker">LAB CAPABILITY</p><h3>科研能力雷达</h3><div class="radar-list"><div v-for="item in researchBi.capability_radar" :key="item.name"><span>{{ item.name }}</span><i><b :style="{ width: item.score + '%' }"></b></i><em>{{ item.score }}</em></div></div><p>评分反映本地资料、项目与成果规划覆盖度，不代表实验室真实能力评级。</p></section></section>

      <section v-if="activeWorkspaceView === 'fde-report'" class="fde-report" aria-label="FDE解决方案报告"><div class="dashboard-heading"><div><p class="section-kicker">FDE SOLUTION DELIVERY</p><h2>FDE 解决方案报告</h2><p>将客户需求、实验室知识资产与 Agent 输出整合为一份可沟通的科研合作交付物。</p></div><button class="outline-button" type="button" @click="applyFdeDeliveryDemo">填充低碳材料案例</button></div><div v-if="!projectMatchResult" class="fde-report-empty"><div class="empty-illustration">◈</div><h3>等待 FDE 交付结果</h3><p>在“客户需求”中创建低碳建筑材料项目并运行需求匹配后，这里会自动汇总真实结果。</p><button class="primary-card-action" type="button" @click="openWorkspaceView('projects')">前往客户需求中心</button></div><div v-else class="fde-report-sheet"><header><span>ResearchOS · 科研合作方案</span><h3>{{ projectMatchResult.projectName }}</h3><p>{{ projectMatchResult.enterprise_requirement }}</p></header><section><b>01</b><div><h4>客户需求理解</h4><p>{{ projectMatchResult.enterprise_requirement }}</p></div></section><section><b>02</b><div><h4>实验室能力匹配</h4><ul><li v-for="item in projectMatchResult.lab_capability_match" :key="item">{{ item }}</li></ul></div></section><section><b>03</b><div><h4>技术路线与方案建议</h4><ul><li v-for="item in projectMatchResult.technical_solution_suggestions" :key="item">{{ item }}</li></ul></div></section><section><b>04</b><div><h4>创新机会</h4><p v-if="researchOsTaskResult?.innovation_opportunities">{{ researchOsTaskResult.innovation_opportunities }}</p><p v-else>运行 Research Master 的“创新发现 Agent”后将在此展示基于资料的创新机会。</p></div></section><section><b>05</b><div><h4>成果规划</h4><dl><template v-for="(value,key) in projectMatchResult.expected_outcome_plan" :key="key"><dt>{{ key }}</dt><dd>{{ Array.isArray(value) ? value.join('、') : value }}</dd></template></dl></div></section><section class="fde-evidence"><b>06</b><div><h4>分析依据</h4><p>以下章节级片段支撑客户需求匹配、技术路线与成果规划建议。</p><ul><li v-for="source in projectMatchResult.sources || []" :key="source.paper_id + source.section">{{ source.paper_title }} · {{ documentTypeLabel(source.document_type) }} · {{ source.section }}</li></ul><p v-if="!(projectMatchResult.sources || []).length">现有团队资料不足，暂无可展示的分析依据。</p></div></section><footer>{{ projectMatchResult.boundary_note }}</footer></div></section>

      <section v-if="activeWorkspaceView === 'system'" class="system-center" aria-label="系统状态中心">
        <div class="dashboard-heading"><div><p class="section-kicker">SYSTEM STATUS CENTER</p><h2>系统状态中心</h2><p>{{ systemStatus?.version || 'ResearchOS v1.0' }} · {{ systemStatus?.platform_name || 'AI科研创新决策平台' }}</p></div><button class="outline-button" type="button" :disabled="systemStatusLoading" @click="loadSystemStatus">{{ systemStatusLoading ? '检查中…' : '刷新状态' }}</button></div>
        <p v-if="systemStatusError" class="error-alert"><span>!</span>{{ systemStatusError }}</p>
        <div v-if="systemStatus" class="system-status-grid"><article v-for="service in systemStatus.services" :key="service.id"><header><span :class="service.status">{{ service.status === 'ready' || service.status === 'configured' ? '正常' : service.status === 'empty' ? '待初始化' : '需配置' }}</span><b>{{ service.name }}</b></header><p>{{ service.detail }}</p></article></div>
        <section class="demo-knowledge-panel"><div><p class="section-kicker">DEMO KNOWLEDGE BASE</p><h3>低碳建筑材料案例资料</h3><p>用于比赛现场讲解知识库、项目资料和产学研协作流程。</p></div><button class="primary-card-action" type="button" @click="initializeDemoKnowledge">{{ demoKnowledgeInitialized ? 'Demo资料已加载' : '初始化 Demo 知识库' }}</button><div v-if="visibleDemoKnowledgeAssets.length" class="demo-asset-grid"><article v-for="asset in visibleDemoKnowledgeAssets" :key="asset.title"><span>{{ asset.status }}</span><h4>{{ asset.title }}</h4><small>{{ asset.type }}</small><p>{{ asset.detail }}</p></article></div><p class="demo-boundary">这些是明确标注的界面展示资料，不会自动写入真实论文库、FAISS 索引或作为 Agent 的科研证据。需要真实分析时，请上传实际可解析的资料。</p></section>
        <section class="activity-log-panel"><div class="result-section-heading"><div><p class="section-kicker">ACTIVITY LOG</p><h3>用户操作日志</h3></div><span>{{ activityLogs.length }} 条</span></div><div v-if="!activityLogs.length" class="activity-empty">暂无操作记录。创建任务、执行 Agent、生成报告或更新项目后会在此显示。</div><ol v-else class="activity-list"><li v-for="item in activityLogs" :key="item.created_at + item.action"><b>{{ item.action }}</b><span>{{ item.detail }}</span><time>{{ formatLibraryDate(item.created_at) }}</time></li></ol></section>
        <p class="demo-boundary">操作日志仅保存在当前浏览器的 localStorage 中，用于现场演示；清除浏览器数据后会被移除。</p>
      </section>

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
    </main>
  `,
}).mount("#app");
