const { computed, createApp, ref } = Vue;

const API_BASE_URL = ["localhost", "127.0.0.1"].includes(window.location.hostname)
  ? "http://127.0.0.1:8000"
  : "https://ai-literature.onrender.com";
const REQUEST_TIMEOUT_MS = 90_000;
const DEFAULT_TASK = "请分析这份文档的核心内容、关键发现、风险与可执行建议。";
const ROLE_OPTIONS = [
  { id: "researcher", name: "研发人员", description: "聚焦技术路线、创新点、技术风险与后续研究。", scenario: "paper", task: "请总结这份技术研究资料，分析核心创新、技术路线、技术风险和后续研究建议。" },
  { id: "product_manager", name: "产品经理", description: "聚焦用户需求、产品价值、功能机会与竞争差异。", scenario: "product_document", task: "请分析这份产品资料的用户需求、产品价值、功能机会、竞争差异和优化建议。" },
  { id: "pre_sales_consultant", name: "售前顾问", description: "聚焦客户需求、方案匹配、实施风险与沟通建议。", scenario: "technical_document", task: "请分析客户需求与方案匹配情况，识别实施风险并给出沟通建议。" },
];
const DEMO_CASES = [
  { name: "新能源汽车技术路线分析", role: "researcher", scenario: "paper", task: "分析新能源汽车技术路线的核心创新、技术风险和后续研究建议。" },
  { name: "竞品产品分析", role: "product_manager", scenario: "product_document", task: "分析这份竞品资料的产品定位、用户价值、功能机会和竞争差异。" },
  { name: "企业解决方案评估", role: "pre_sales_consultant", scenario: "technical_document", task: "分析该企业解决方案的客户需求匹配、核心模块、实施风险和沟通建议。" },
];
const FULL_DEMO_CASE = {
  name: "体验完整案例",
  role: "pre_sales_consultant",
  scenario: "technical_document",
  task: "分析某企业技术方案的方案优势、实施风险，并给出客户沟通建议。",
};
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

    const selectedScenario = computed(() => (
      SCENARIO_OPTIONS.find((item) => item.id === scenario.value) || SCENARIO_OPTIONS[0]
    ));
    const selectedRole = computed(() => (
      ROLE_OPTIONS.find((item) => item.id === role.value) || ROLE_OPTIONS[0]
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
    }

    function applyDemo(item) {
      role.value = item.role;
      scenario.value = item.scenario;
      task.value = item.task;
      errorMessage.value = "";
    }

    function applyFullDemo() {
      applyDemo(FULL_DEMO_CASE);
      errorMessage.value = "完整案例已填充，请上传一份可提取文本的 PDF 后开始真实分析。";
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
        errorMessage.value = "请输入分析任务。";
        return;
      }

      loading.value = true;
      errorMessage.value = "";
      result.value = null;
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
      if (fileInput.value) fileInput.value.value = "";
    }

    return {
      agentDecision,
      agentTrace,
      analysisData,
      analysisEntries,
      analyzeDocument,
      asking,
      askQuestion,
      chatMessages,
      businessReport,
      clearCurrentDocument,
      decisionReport,
      demoCases: DEMO_CASES,
      evidenceCards,
      evidenceSources,
      errorMessage,
      fileInput,
      fileSizeLabel,
      formatResultKey,
      loading,
      onFileChange,
      question,
      reportTitle,
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
      selectedScenario,
      task,
      qualityCheck,
      trustReport,
      uploadStatus,
      valueEstimation,
    };
  },
  template: `
    <main class="app-shell">
      <header class="topbar">
        <div>
          <p class="product-mark"><span></span> AI INSIGHT AGENT</p>
          <h1>AI Insight Agent</h1>
          <p class="hero-subtitle">企业知识洞察与决策支持助手</p>
          <p class="product-description">让企业知识快速转化为决策能力</p>
          <div class="hero-value-list"><span>理解复杂资料</span><span>发现关键风险</span><span>生成行动建议</span></div>
        </div>
        <div class="topbar-status"><i></i> Agent 已就绪</div>
      </header>

      <section class="role-use-cases" aria-label="适用岗位">
        <div><p class="section-kicker">BUILT FOR TEAMS</p><h2>适用于</h2></div>
        <article><b>研发工程师</b><span>快速理解技术资料</span></article>
        <article><b>产品经理</b><span>发现产品机会</span></article>
        <article><b>售前顾问</b><span>快速准备客户方案</span></article>
      </section>

      <p v-if="errorMessage" class="error-alert" role="alert">
        <span>!</span>{{ errorMessage }}
      </p>

      <section class="workspace-grid">
        <aside class="control-panel">
          <div class="panel-heading">
            <p class="section-kicker">WORKSPACE</p>
            <h2>配置你的 Agent 任务</h2>
          </div>

          <section class="role-section" aria-label="用户角色选择">
            <div class="step-label"><b>Step 1</b><label>选择用户角色</label></div>
            <div class="role-options">
              <button v-for="item in roleOptions" :key="item.id" type="button" class="role-option" :class="{ active: role === item.id }" @click="selectRole(item)">
                <strong>{{ item.name }}</strong><small>{{ item.description }}</small>
              </button>
            </div>
          </section>

          <section class="scenario-section" aria-label="应用场景选择">
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
          </section>

          <div class="task-section">
            <div class="label-row">
              <span class="step-label"><b>Step 3</b><label for="task">输入用户目标</label></span>
              <button class="text-button" type="button" @click="resetTask">恢复默认</button>
            </div>
            <textarea id="task" v-model="task" rows="6"></textarea>
            <p class="field-hint">当前角色：{{ selectedRole.name }}。Agent 会据此调整分析重点和业务报告。</p>
          </div>

          <section class="demo-section" aria-label="预置演示案例">
            <div class="label-row"><label>Demo 展示模式</label><button class="full-demo-button" type="button" @click="applyFullDemo">3分钟体验Demo</button></div>
            <div class="demo-case-list"><button v-for="item in demoCases" :key="item.name" type="button" @click="applyDemo(item)">{{ item.name }}</button></div>
            <ol class="demo-flow"><li><b>01</b>理解客户需求</li><li><b>02</b>分析技术方案</li><li><b>03</b>识别风险</li><li><b>04</b>生成沟通策略</li></ol>
          </section>

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
            <button v-if="result" class="outline-button" :disabled="loading" @click="analyzeDocument">重新分析</button>
          </div>

          <div v-if="loading" class="loading-state">
            <div class="process-heading">
              <span class="spinner"></span>
              <div><h3>Agent 正在处理文档</h3><p>请求已发送，正在等待后端完成 PDF 解析、任务规划与模型分析。</p></div>
            </div>
          </div>

          <div v-else-if="!result" class="empty-state">
            <div class="empty-illustration">⌁</div>
            <h3>等待开始分析</h3>
            <p>选择场景、输入目标并上传 PDF 文档后，结果会显示在这里。</p>
          </div>

          <div v-else class="analysis-content">
            <section v-if="agentTrace" class="agent-trace-summary" aria-label="AI如何完成这次分析">
              <div class="agent-decision-heading"><div><p class="section-kicker">EXECUTION SUMMARY</p><h3>AI如何完成这次分析</h3></div><span class="agent-trace-status">执行摘要</span></div>
              <div class="trace-row"><span>用户目标</span><p>{{ agentTrace.user_goal }}</p></div>
              <div class="trace-row"><span>用户角色</span><p>{{ agentTrace.user_role }}</p></div>
              <div class="trace-row"><span>分析策略</span><p>{{ agentTrace.analysis_strategy }}</p></div>
              <div v-if="agentTrace.selected_tools?.length" class="trace-row"><span>已用能力</span><div class="task-chip-list"><b v-for="item in agentTrace.selected_tools" :key="item">{{ item }}</b></div></div>
              <div v-if="agentTrace.execution_steps?.length" class="trace-row trace-plan-row"><span>执行步骤</span><ol class="agent-execution-plan"><li v-for="step in agentTrace.execution_steps" :key="step"><i>✓</i>{{ step }}</li></ol></div>
              <p class="trace-boundary">此处展示的是后端真实执行流程摘要，不展示模型内部思维过程。</p>
            </section>

            <section v-if="agentDecision" class="agent-decision" aria-label="Agent执行过程">
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
            </section>

            <section v-if="trustReport" class="trust-report" aria-label="结果可信度中心">
              <div class="trust-report-heading"><div><p class="section-kicker">TRUST CENTER</p><h3>结果可信度中心</h3></div><strong v-if="trustReport.confidenceScore !== null">{{ trustReport.confidenceScore }}<small>/100</small></strong></div>
              <p class="trust-note">该评分基于当前结构化结果的字段覆盖与缺失信息规则计算，不代表事实正确率。</p>
              <div class="trust-grid"><article><h4>信息依据</h4><ul><li v-for="item in trustReport.informationBasis" :key="item">{{ item }}</li></ul></article><article><h4>不确定性</h4><ul><li v-for="item in trustReport.uncertainties" :key="item">{{ item }}</li></ul></article><article><h4>验证建议</h4><ul><li v-for="item in trustReport.verificationSuggestions" :key="item">{{ item }}</li></ul></article></div>
            </section>

            <section v-if="valueEstimation" class="value-estimation" aria-label="业务价值量化模拟">
              <div><p class="section-kicker">VALUE ESTIMATION</p><h3>业务价值说明</h3></div>
              <div class="value-estimation-grid"><article><h4>时间节省</h4><p>{{ valueEstimation.time_saved }}</p></article><article><h4>决策辅助</h4><p>{{ valueEstimation.decision_support }}</p></article><article><h4>应用场景</h4><p>{{ valueEstimation.application_scene }}</p></article></div>
              <p>仅描述定性价值，不虚构节省比例、准确率或业务收益数据。</p>
            </section>

            <section v-if="businessReport" class="business-report" aria-label="AI业务价值报告">
              <div class="business-report-heading"><div><p class="section-kicker">BUSINESS INSIGHT</p><h3>AI业务价值报告</h3></div><span>后端真实返回</span></div>
              <div v-if="businessReport.decisionSummary" class="business-summary"><span>决策摘要</span><p>{{ businessReport.decisionSummary }}</p></div>
              <div class="business-report-grid">
                <article v-if="businessReport.importantFindings.length"><h4>重要发现</h4><ul><li v-for="item in businessReport.importantFindings" :key="item">{{ item }}</li></ul></article>
                <article v-if="businessReport.businessOpportunities.length"><h4>业务机会</h4><ul><li v-for="item in businessReport.businessOpportunities" :key="item">{{ item }}</li></ul></article>
                <article v-if="businessReport.risks.length"><h4>风险提示</h4><ul><li v-for="item in businessReport.risks" :key="item">{{ item }}</li></ul></article>
                <article v-if="businessReport.recommendedActions.length"><h4>推荐行动</h4><ul><li v-for="item in businessReport.recommendedActions" :key="item">{{ item }}</li></ul></article>
              </div>
              <div v-if="businessReport.expectedValue" class="business-summary"><span>预期价值</span><p>{{ businessReport.expectedValue }}</p></div>
            </section>

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

            <section v-if="evidenceSources.length" class="evidence-section" aria-label="证据来源">
              <div><p class="section-kicker">EXPLAINABILITY</p><h3>证据来源</h3></div>
              <p>当前 MVP 提供文档章节级提示，尚未实现精确页码与段落定位。</p>
              <ul><li v-for="item in evidenceSources" :key="item.field"><b>{{ formatResultKey(item.field) }}</b><span>{{ item.source_section }}</span></li></ul>
            </section>

            <section v-if="evidenceCards.length" class="evidence-cards" aria-label="关键结论证据卡">
              <div><p class="section-kicker">EVIDENCE CARDS</p><h3>关键结论与依据</h3></div>
              <article v-for="item in evidenceCards" :key="item.finding"><p>{{ item.finding }}</p><div><span>📌 依据：{{ item.source }}</span><b>可信程度：{{ item.support_level === 'high' ? '高' : '中' }}</b></div></article>
            </section>

            <section v-if="qualityCheck" class="quality-check" aria-label="技术信息">
              <div><p class="section-kicker">TECHNICAL INFORMATION</p><h3>技术信息</h3></div>
              <p><b>结构化结果完整度：</b>{{ qualityCheck.completeness ? "完整" : "存在待补充信息" }}</p>
              <p><b>规则质量评分：</b>{{ qualityCheck.score }}/100</p>
              <p v-if="qualityCheck.missing_information?.length"><b>待补充：</b>{{ qualityCheck.missing_information.join("、") }}</p>
            </section>
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
    </main>
  `,
}).mount("#app");
