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
    const activeWorkspaceView = ref("assistant");
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
      if (view === "library") await loadLibraryPapers();
      if (view === "reports") await loadResearchReports();
      if (view === "rag") {
        await loadLibraryPapers();
        await loadRagHistory();
      }
      void loadResearchOverview();
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
        const response = await fetchWithTimeout(`${API_BASE_URL}/research/papers/upload`, {
          method: "POST",
          body: formData,
        });
        selectedLibraryPaper.value = await readResponse(response);
        libraryPaperDetail.value = null;
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
          <button class="brand-button" type="button" @click="openWorkspaceView('assistant')"><span class="brand-orb">✦</span><span>AI Research Agent</span></button>
          <div class="top-navigation-links"><button type="button" :class="{ active: activeWorkspaceView === 'assistant' }" @click="openWorkspaceView('assistant')">AI助手</button><button type="button" :class="{ active: activeWorkspaceView === 'library' }" @click="openWorkspaceView('library')">论文库</button><button type="button" :class="{ active: activeWorkspaceView === 'reports' }" @click="openWorkspaceView('reports')">研究报告</button><button type="button" :class="{ active: activeWorkspaceView === 'rag' }" @click="openWorkspaceView('rag')">知识问答</button></div>
          <span class="top-navigation-status"><i></i> Online</span>
        </nav>
        <div v-if="activeWorkspaceView === 'assistant'" class="minimal-hero">
          <h1>AI Research Agent</h1>
          <p>让 AI 帮助你理解论文、探索知识、生成研究洞察。</p>
          <div class="hero-tags" aria-label="核心能力"><span>📄 论文分析</span><span>🔍 知识检索</span><span>🧠 研究生成</span></div>
          <label class="hero-input"><span>✦</span><input v-model="task" placeholder="上传论文后，告诉 AI 你想研究什么" /><button type="button" @click="openWorkspaceView('assistant')">开始</button></label>
        </div>
      </header>

      <section v-if="activeWorkspaceView === 'library'" class="library-workspace" aria-label="我的论文库">
        <div class="library-header"><div><p class="section-kicker">MY PAPER LIBRARY</p><h2>我的论文库</h2><p>已保存并解析的科研资料，可直接进入 AI助手分析。</p></div><div class="library-header-actions"><label class="library-upload-button" :class="{ busy: libraryUploading }"><input ref="libraryFileInput" type="file" accept="application/pdf,.pdf" :disabled="libraryUploading" @change="uploadLibraryPaper" /><span>{{ libraryUploading ? '正在保存论文…' : '＋ 上传论文' }}</span></label><button class="outline-button" type="button" :disabled="libraryLoading" @click="loadLibraryPapers">{{ libraryLoading ? '刷新中' : '刷新列表' }}</button></div></div>
        <div v-if="libraryPapers.length" class="library-toolbar"><label><span>⌕</span><input v-model="librarySearch" type="search" placeholder="搜索论文标题或文件名" /></label><select v-model="libraryStatusFilter" aria-label="按知识库状态筛选"><option value="all">全部状态</option><option value="ready">Ready</option><option value="indexed">Indexed</option><option value="parsed">Parsed</option><option value="failed">Failed</option></select><small>共 {{ filteredLibraryPapers.length }} / {{ libraryPapers.length }} 篇资料</small></div>
        <p v-if="libraryError" class="error-alert" role="alert"><span>!</span>{{ libraryError }}</p>
        <div v-if="libraryLoading && !libraryPapers.length" class="library-empty-state"><span class="spinner"></span><p>正在加载论文库…</p></div>
        <div v-else-if="!libraryPapers.length" class="library-empty-state"><div class="empty-illustration">▣</div><h3>暂无科研资料，上传第一篇论文开始分析</h3><p>上传可提取文本的 PDF 后，它会成为科研知识空间中的一份资料。</p></div>
        <div v-else-if="!filteredLibraryPapers.length" class="library-empty-state"><div class="empty-illustration">⌕</div><h3>没有匹配的科研资料</h3><p>试试调整关键词或知识库状态筛选条件。</p></div>
        <div v-else class="library-layout"><div class="paper-card-list"><article v-for="paper in filteredLibraryPapers" :key="paper.paper_id" class="paper-library-card" :class="{ selected: selectedLibraryPaper?.paper_id === paper.paper_id }"><div class="paper-card-top"><span class="paper-status">{{ paper.quality_status || libraryStatusLabel(paper.analysis_status) }}</span><details class="paper-more"><summary aria-label="更多操作">•••</summary><button type="button" @click="deleteLibraryPaper(paper)">删除论文</button></details></div><h3>{{ paper.title }}</h3><p class="paper-filename">{{ paper.filename }}</p><div class="paper-meta"><span>{{ paper.chunk_count ?? 0 }} 个知识片段</span><span>{{ formatLibraryDate(paper.updated_at || paper.upload_time) }}</span></div><div class="paper-card-actions"><button type="button" class="primary-card-action" :disabled="libraryAnalysisLoading" @click="analyzeLibraryPaper(paper)">{{ libraryAnalysisLoading && selectedLibraryPaper?.paper_id === paper.paper_id ? '分析中…' : '分析' }}</button><button type="button" class="text-button" @click="viewLibraryPaper(paper)">详情</button></div></article></div><aside v-if="libraryPaperDetail" class="library-detail-panel"><div class="library-detail-heading"><div><p class="section-kicker">PAPER DETAIL</p><h3>{{ libraryPaperDetail.title }}</h3></div><button type="button" class="text-button" @click="libraryPaperDetail = null">关闭</button></div><dl><div><dt>文件名</dt><dd>{{ libraryPaperDetail.filename }}</dd></div><div><dt>知识库状态</dt><dd>{{ libraryPaperDetail.quality_status || libraryStatusLabel(libraryPaperDetail.analysis_status) }}</dd></div><div><dt>知识片段</dt><dd>{{ libraryPaperDetail.chunk_count ?? 0 }} 个</dd></div><div><dt>更新时间</dt><dd>{{ formatLibraryDate(libraryPaperDetail.updated_at || libraryPaperDetail.upload_time) }}</dd></div><div><dt>文本长度</dt><dd>{{ formatTextLength(libraryPaperDetail.text_length) }}</dd></div></dl><button type="button" class="analyze-button" :disabled="libraryAnalysisLoading" @click="analyzeLibraryPaper(libraryPaperDetail)">{{ libraryAnalysisLoading ? '正在进入 AI助手分析…' : '进入 AI 分析' }}</button></aside></div>
      </section>

      <section v-if="activeWorkspaceView === 'reports'" class="research-reports" aria-label="研究报告历史">
        <div class="library-header"><div><p class="section-kicker">RESEARCH REPORTS</p><h2>研究报告</h2><p>这里保存从论文库进入 AI 助手后生成的分析记录。查看报告会回到原有 AI助手结果区。</p></div><div class="library-header-actions"><button class="outline-button" type="button" :disabled="reportsLoading" @click="loadResearchReports">{{ reportsLoading ? '刷新中' : '刷新报告' }}</button></div></div>
        <p v-if="reportsError" class="error-alert" role="alert"><span>!</span>{{ reportsError }}</p>
        <div v-if="reportsLoading && !reportRecords.length" class="library-empty-state"><span class="spinner"></span><p>正在读取研究报告…</p></div>
        <div v-else-if="!reportRecords.length" class="library-empty-state"><div class="empty-illustration">▤</div><h3>暂无历史研究报告</h3><p>从“我的论文库”进入 AI 分析后，报告会自动保存在这里。</p></div>
        <div v-else class="report-record-list"><article v-for="report in reportRecords" :key="report.id" class="report-record-card" :class="{ selected: selectedReport?.id === report.id }"><div><span class="paper-status">{{ report.scenario }}</span><time>{{ formatLibraryDate(report.created_at) }}</time></div><h3>{{ report.paper_title }}</h3><p>{{ report.task }}</p><footer><span>{{ report.role }}</span><button type="button" class="primary-card-action" :disabled="reportDetailLoading" @click="viewResearchReport(report)">{{ reportDetailLoading && selectedReport?.id === report.id ? '正在恢复…' : '查看报告' }}</button></footer></article></div>
      </section>

      <section v-if="activeWorkspaceView === 'rag'" class="rag-workspace" aria-label="科研知识问答">
        <div class="library-header"><div><p class="section-kicker">MULTI-PAPER RAG</p><h2>科研知识问答</h2><p>Agent 会检索论文库中的相关片段，再基于引用证据回答问题。</p></div><div class="library-header-actions"><button class="outline-button" type="button" :disabled="libraryLoading" @click="loadLibraryPapers">{{ libraryLoading ? '刷新中' : '刷新论文范围' }}</button></div></div>
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
