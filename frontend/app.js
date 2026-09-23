const { computed, createApp, ref } = Vue;

const API_BASE_URL = ["localhost", "127.0.0.1"].includes(window.location.hostname)
  ? "http://127.0.0.1:8000"
  : "https://ai-literature.onrender.com";
const REQUEST_TIMEOUT_MS = 90_000;
const DEFAULT_TASK = "请分析这篇论文的研究主题、研究问题、研究方法、主要结果、创新点和局限性。";

createApp({
  setup() {
    const task = ref(DEFAULT_TASK);
    const selectedFile = ref(null);
    const fileInput = ref(null);
    const result = ref(null);
    const question = ref("");
    const chatMessages = ref([]);
    const loading = ref(false);
    const asking = ref(false);
    const errorMessage = ref("");

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

    const analysisCards = computed(() => {
      const analysis = result.value?.analysis || result.value?.result;
      if (!analysis) return [];
      return [
        { key: "research_topic", title: "研究主题", value: analysis.research_topic },
        { key: "research_question", title: "研究问题", value: analysis.research_question },
        { key: "methodology", title: "研究方法", value: analysis.methodology },
        { key: "key_findings", title: "核心发现", value: analysis.key_findings },
        { key: "innovation_points", title: "创新点", value: analysis.innovation_points },
        { key: "limitations", title: "局限性", value: analysis.limitations },
        { key: "keywords", title: "关键词", value: analysis.keywords, tags: true },
      ];
    });

    const analysisData = computed(() => result.value?.analysis || result.value?.result || {});

    const agentDecision = computed(() => {
      if (!result.value) return null;
      const detectedTasks = Array.isArray(result.value.detected_tasks)
        ? result.value.detected_tasks
        : [];
      const executionPlan = Array.isArray(result.value.execution_plan)
        ? result.value.execution_plan
        : [];
      const userTask = result.value.user_task || result.value.task || "";
      const decisionReason = result.value.decision_reason || "";

      if (!userTask && !detectedTasks.length && !decisionReason && !executionPlan.length) {
        return null;
      }
      return { userTask, detectedTasks, decisionReason, executionPlan };
    });

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
        if (timedOut) throw new Error("请求超时，请稍后重试或上传篇幅更短的论文。");
        if (error instanceof TypeError) {
          throw new Error("无法连接后端服务，请确认后端已启动后重试。");
        }
        throw error;
      } finally {
        window.clearTimeout(timeout);
      }
    }

    async function analyzePaper() {
      if (loading.value) return;
      if (!selectedFile.value) {
        errorMessage.value = "请先选择一篇 PDF 文件。";
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
        const response = await fetchWithTimeout(`${API_BASE_URL}/agent/analyze-paper`, {
          method: "POST",
          body: formData,
        });
        result.value = await readResponse(response);
        chatMessages.value.push({
          role: "assistant",
          content: "论文分析已完成。你可以继续针对研究方法、实验设计或结论提问。",
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
      task.value = DEFAULT_TASK;
    }

    function clearCurrentPaper() {
      selectedFile.value = null;
      result.value = null;
      question.value = "";
      chatMessages.value = [];
      errorMessage.value = "";
      if (fileInput.value) fileInput.value.value = "";
    }

    return {
      analysisCards,
      agentDecision,
      asking,
      analysisData,
      chatMessages,
      clearCurrentPaper,
      errorMessage,
      fileInput,
      fileSizeLabel,
      loading,
      onFileChange,
      askQuestion,
      analyzePaper,
      question,
      resetTask,
      result,
      selectedFile,
      task,
      uploadStatus,
    };
  },
  template: `
    <main class="app-shell">
      <header class="topbar">
        <div>
          <p class="product-mark"><span></span> RESEARCH AI</p>
          <h1>AI 科研文献分析助手</h1>
          <p class="product-description">上传论文，用清晰的结构化视角快速理解研究价值。</p>
        </div>
        <div class="topbar-status"><i></i> Agent 已就绪</div>
      </header>

      <p v-if="errorMessage" class="error-alert" role="alert">
        <span>!</span>{{ errorMessage }}
      </p>

      <section class="workspace-grid">
        <aside class="control-panel">
          <div class="panel-heading">
            <p class="section-kicker">WORKSPACE</p>
            <h2>论文与任务</h2>
          </div>

          <label class="upload-box" :class="{ 'has-file': selectedFile }" for="pdf-file">
            <input ref="fileInput" id="pdf-file" type="file" accept="application/pdf,.pdf" @change="onFileChange" />
            <span class="upload-icon">⇧</span>
            <strong>{{ selectedFile ? "更换 PDF 文件" : "上传论文 PDF" }}</strong>
            <small>支持可提取文本的 PDF</small>
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

          <div class="task-section">
            <div class="label-row">
              <label for="task">分析任务</label>
              <button class="text-button" type="button" @click="resetTask">恢复默认</button>
            </div>
            <textarea id="task" v-model="task" rows="6"></textarea>
            <p class="field-hint">Agent 会识别任务重点，并选择对应的分析流程。</p>
          </div>

          <button class="analyze-button" :disabled="loading" @click="analyzePaper">
            <span v-if="loading" class="spinner small-spinner"></span>
            {{ loading ? "正在分析论文..." : "开始分析" }}
          </button>
          <button v-if="result" class="clear-button" type="button" @click="clearCurrentPaper">清空当前论文</button>
        </aside>

        <section class="result-panel">
          <div class="result-header">
            <div>
              <p class="section-kicker">ANALYSIS</p>
              <h2>论文分析结果</h2>
            </div>
            <button v-if="result" class="outline-button" :disabled="loading" @click="analyzePaper">重新分析</button>
          </div>

          <div v-if="loading" class="loading-state">
            <div class="process-heading">
              <span class="spinner"></span>
              <div><h3>正在请求 Agent 分析论文</h3><p>后端处理完成后，将展示实际返回的决策过程。</p></div>
            </div>
          </div>

          <div v-else-if="!result" class="empty-state">
            <div class="empty-illustration">⌁</div>
            <h3>等待开始分析</h3>
            <p>上传一篇 PDF，设置分析任务后，结果会显示在这里。</p>
          </div>

          <div v-else class="analysis-content">
            <section v-if="agentDecision" class="agent-decision" aria-label="Agent执行过程">
              <div class="agent-decision-heading">
                <div>
                  <p class="section-kicker">AGENT TRACE</p>
                  <h3>Agent执行过程</h3>
                </div>
                <span class="agent-trace-status">后端真实返回</span>
              </div>

              <div v-if="agentDecision.userTask" class="trace-row">
                <span>用户任务</span><p>{{ agentDecision.userTask }}</p>
              </div>
              <div v-if="agentDecision.detectedTasks.length" class="trace-row">
                <span>任务识别结果</span>
                <div class="task-chip-list"><b v-for="item in agentDecision.detectedTasks" :key="item">{{ item }}</b></div>
              </div>
              <div v-if="agentDecision.decisionReason" class="trace-row">
                <span>决策原因</span><p>{{ agentDecision.decisionReason }}</p>
              </div>
              <div v-if="agentDecision.executionPlan.length" class="trace-row trace-plan-row">
                <span>执行计划</span>
                <ol class="agent-execution-plan">
                  <li v-for="step in agentDecision.executionPlan" :key="step"><i>✓</i>{{ step }}</li>
                </ol>
              </div>
            </section>

            <div class="paper-title-row">
              <div>
                <span class="result-label">论文标题</span>
                <h3>{{ analysisData.title || "论文未说明" }}</h3>
              </div>
              <span class="status-pill">{{ result.task_type || "论文整体分析" }}</span>
            </div>

            <div class="analysis-grid">
              <article v-for="card in analysisCards" :key="card.key" class="analysis-card" :class="{ 'keyword-card': card.tags }">
                <h3>{{ card.title }}</h3>
                <template v-if="Array.isArray(card.value)">
                  <ul v-if="!card.tags" class="finding-list">
                    <li v-for="item in card.value" :key="item">{{ item }}</li>
                    <li v-if="!card.value.length">论文未说明</li>
                  </ul>
                  <div v-else class="keyword-list">
                    <span v-for="item in card.value" :key="item">{{ item }}</span>
                    <em v-if="!card.value.length">论文未说明</em>
                  </div>
                </template>
                <p v-else>{{ card.value || "论文未说明" }}</p>
              </article>
            </div>
          </div>
        </section>
      </section>

      <section class="chat-panel">
        <div class="chat-header">
          <div>
            <p class="section-kicker">FOLLOW-UP</p>
            <h2>继续追问论文</h2>
          </div>
          <span v-if="result" class="context-note">已连接当前论文</span>
        </div>

        <div v-if="!result" class="chat-empty">完成论文分析后，即可在这里继续对话。</div>
        <div v-else class="messages" aria-live="polite">
          <div v-for="(message, index) in chatMessages" :key="index" class="message-row" :class="message.role">
            <span class="message-avatar">{{ message.role === "user" ? "你" : "AI" }}</span>
            <p>{{ message.content }}</p>
          </div>
          <div v-if="asking" class="message-row assistant thinking-message">
            <span class="message-avatar">AI</span><p><span class="typing-dot"></span><span class="typing-dot"></span><span class="typing-dot"></span></p>
          </div>
        </div>

        <div class="chat-composer" :class="{ disabled: !result }">
          <input v-model="question" :disabled="!result || asking" placeholder="例如：这个研究方法有什么优势？" @keyup.enter="askQuestion" />
          <button :disabled="!result || !question.trim() || asking" @click="askQuestion">
            {{ asking ? "思考中" : "发送" }} <span>→</span>
          </button>
        </div>
      </section>
    </main>
  `,
}).mount("#app");
