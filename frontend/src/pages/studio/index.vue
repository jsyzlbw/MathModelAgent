<script setup lang="ts">
import {
	type GuiConfig,
	type ArtifactItem,
	type ChatMessageRecord,
	type ProgressEvent,
	type RagCaseItem,
	type RagGuideResponse,
	type RevisionRequestRecord,
	type UploadedWorkspaceFile,
	type WorkspaceFileKind,
	type WorkspacePlan,
	appendChatMessage,
	applyWorkspacePlanAction,
	createGuiWorkspace,
	createRevisionRequest,
	draftWorkspacePlan,
	getWorkspaceArtifactDownloadUrl,
	getWorkspaceEvents,
	getRagGuide,
	listWorkspaceArtifacts,
	listRagCases,
	type ProviderTestResponse,
	getGuiConfig,
	listChatMessages,
	listRevisionRequests,
	readWorkspaceArtifact,
	rebuildRagIndex,
	resumeWorkspace,
	runWorkspace,
	saveGuiConfig,
	stopWorkspace,
	testGuiProvider,
	uploadWorkspaceFiles,
} from "@/apis/guiApi";
import { Button } from "@/components/ui/button";
import {
	Card,
	CardContent,
	CardDescription,
	CardHeader,
	CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import { useToast } from "@/components/ui/toast/use-toast";
import {
	Activity,
	Archive,
	Ban,
	BookOpen,
	Bot,
	CheckCircle2,
	Database,
	FileUp,
	HelpCircle,
	MessageSquare,
	Play,
	RefreshCw,
	Save,
	Settings,
	SkipForward,
	Square,
	UploadCloud,
} from "lucide-vue-next";
import { computed, onBeforeUnmount, onMounted, ref } from "vue";

type ConfigPath = string[];

interface ApiRowDefinition {
	provider: string;
	label: string;
	path: ConfigPath;
	secretKey?: string;
	fields: Array<{
		key: string;
		label: string;
		placeholder?: string;
		type?: "text" | "number";
	}>;
}

interface ApiRowForm {
	values: Record<string, string>;
	secret: string;
	configured: boolean;
	preview: string;
	testing: boolean;
	result: ProviderTestResponse | null;
}

interface LocalMessage {
	id?: string;
	role: "user" | "agent";
	content: string;
	createdAt: string;
}

const { toast } = useToast();

const activeTaskId = ref("");
const workspaceTitle = ref("MCM/ICM Workspace");
const planDraft = ref(
	"1. 理解题意并拆解子问题\n2. 讨论候选模型和数据需求\n3. 生成代码实验与图表\n4. 写作论文并进行审稿修订",
);
const chatInput = ref("");
const problemText = ref("");
const localMessages = ref<LocalMessage[]>([
	{
		role: "agent",
		content: "请先配置 API、导入/确认知识库结构，再上传本次题目。我会根据你的意见整理执行计划。",
		createdAt: new Date().toISOString(),
	},
]);
const running = ref(false);
const progressEvents = ref<ProgressEvent[]>([]);
const eventCursor = ref(0);
const artifacts = ref<ArtifactItem[]>([]);
const artifactPreview = ref<{ path: string; content: string } | null>(null);
const artifactLoading = ref(false);
const ragCases = ref<RagCaseItem[]>([]);
const ragGuide = ref<RagGuideResponse | null>(null);
const ragLoading = ref(false);
const ragRebuilding = ref(false);
const ragIndexMessage = ref("");
const currentPlan = ref<WorkspacePlan | null>(null);
const planningBusy = ref(false);
const revisionRequests = ref<RevisionRequestRecord[]>([]);
const revisionBusy = ref(false);
let progressTimer: ReturnType<typeof setInterval> | null = null;

const apiRowDefs: ApiRowDefinition[] = [
	{
		provider: "coordinator",
		label: "协调者 LLM",
		path: ["llm", "coordinator"],
		secretKey: "api_key",
		fields: [
			{ key: "api_type", label: "API Type", placeholder: "openai-chat" },
			{ key: "model", label: "Model", placeholder: "gpt-4o" },
			{ key: "base_url", label: "Base URL", placeholder: "https://api.openai.com/v1" },
			{ key: "context_window", label: "Context", type: "number" },
		],
	},
	{
		provider: "modeler",
		label: "建模手 LLM",
		path: ["llm", "modeler"],
		secretKey: "api_key",
		fields: [
			{ key: "api_type", label: "API Type", placeholder: "openai-chat" },
			{ key: "model", label: "Model" },
			{ key: "base_url", label: "Base URL" },
			{ key: "context_window", label: "Context", type: "number" },
		],
	},
	{
		provider: "coder",
		label: "代码手 LLM",
		path: ["llm", "coder"],
		secretKey: "api_key",
		fields: [
			{ key: "api_type", label: "API Type", placeholder: "openai-chat" },
			{ key: "model", label: "Model" },
			{ key: "base_url", label: "Base URL" },
			{ key: "context_window", label: "Context", type: "number" },
		],
	},
	{
		provider: "writer",
		label: "论文手 LLM",
		path: ["llm", "writer"],
		secretKey: "api_key",
		fields: [
			{ key: "api_type", label: "API Type", placeholder: "openai-chat" },
			{ key: "model", label: "Model" },
			{ key: "base_url", label: "Base URL" },
			{ key: "context_window", label: "Context", type: "number" },
		],
	},
	{
		provider: "tavily",
		label: "Tavily Search",
		path: ["search", "tavily"],
		secretKey: "api_key",
		fields: [],
	},
	{
		provider: "brave",
		label: "Brave Search",
		path: ["search", "brave"],
		secretKey: "api_key",
		fields: [],
	},
	{
		provider: "exa",
		label: "Exa Search",
		path: ["search", "exa"],
		secretKey: "api_key",
		fields: [],
	},
	{
		provider: "firecrawl",
		label: "Firecrawl",
		path: ["search", "firecrawl"],
		secretKey: "api_key",
		fields: [],
	},
	{
		provider: "openalex",
		label: "OpenAlex",
		path: ["academic", "openalex"],
		secretKey: "api_key",
		fields: [{ key: "email", label: "Email", placeholder: "you@example.com" }],
	},
	{
		provider: "mineru",
		label: "MinerU",
		path: ["document", "mineru"],
		secretKey: "api_key",
		fields: [
			{ key: "mode", label: "Mode", placeholder: "fake / cli / api" },
			{ key: "api_base_url", label: "Base URL" },
			{ key: "cli", label: "CLI", placeholder: "mineru" },
		],
	},
	{
		provider: "humanizer",
		label: "Humanizer",
		path: ["humanizer"],
		secretKey: "api_key",
		fields: [{ key: "api_base_url", label: "Base URL" }],
	},
	{
		provider: "fred",
		label: "FRED",
		path: ["official_data", "fred"],
		secretKey: "api_key",
		fields: [],
	},
	{
		provider: "us_census",
		label: "US Census",
		path: ["official_data", "us_census"],
		secretKey: "api_key",
		fields: [],
	},
	{
		provider: "noaa",
		label: "NOAA",
		path: ["official_data", "noaa"],
		secretKey: "api_key",
		fields: [],
	},
];

const configLoading = ref(false);
const configSaving = ref(false);
const configError = ref("");
const maskedConfig = ref<GuiConfig>({});
const apiForms = ref<Record<string, ApiRowForm>>({});
const workspaceCreating = ref(false);
const uploadStatus = ref<Record<string, UploadedWorkspaceFile[]>>({});
const uploadingKind = ref<WorkspaceFileKind | null>(null);

const configuredCount = computed(
	() => Object.values(apiForms.value).filter((form) => form.configured).length,
);

const ragKnowledgeDir = computed(() => {
	const rag = getNode(maskedConfig.value, ["rag"]);
	return String(rag.knowledge_base_dir ?? "data/rag_cases");
});

const uploadKinds = [
	{ key: "problem" as const, label: "赛题文件", icon: FileUp },
	{ key: "attachment" as const, label: "题目附件", icon: Database },
	{ key: "template" as const, label: "格式样例", icon: Archive },
	{ key: "requirement" as const, label: "其他要求", icon: UploadCloud },
	{ key: "chat" as const, label: "对话附件", icon: MessageSquare },
];

const displayedProgressEvents = computed(() => {
	if (progressEvents.value.length) return progressEvents.value;
	return [
		{
			seq: 0,
			timestamp: "",
			level: "info",
			stage: "workspace.pending",
			message: "等待创建工作区并启动任务",
			metadata: {},
		},
	];
});

const displayedArtifacts = computed(() => {
	if (artifacts.value.length) return artifacts.value;
	return [
		{ path: "res.md", filename: "res.md", file_type: "markdown", size: 0 },
		{ path: "res.pdf", filename: "res.pdf", file_type: "pdf", size: 0 },
		{ path: "figures/", filename: "figures", file_type: "folder", size: 0 },
	];
});

const latestRevisionRequest = computed(() => {
	if (!revisionRequests.value.length) return null;
	return revisionRequests.value[revisionRequests.value.length - 1];
});

const isPlainObject = (value: unknown): value is Record<string, unknown> => {
	return !!value && typeof value === "object" && !Array.isArray(value);
};

const getNode = (
	source: Record<string, unknown>,
	path: ConfigPath,
): Record<string, unknown> => {
	let current: unknown = source;
	for (const key of path) {
		if (!isPlainObject(current)) return {};
		current = current[key];
	}
	return isPlainObject(current) ? current : {};
};

const setNodeValue = (
	target: Record<string, unknown>,
	path: ConfigPath,
	key: string,
	value: unknown,
) => {
	let current = target;
	for (const part of path) {
		if (!isPlainObject(current[part])) {
			current[part] = {};
		}
		current = current[part] as Record<string, unknown>;
	}
	current[key] = value;
};

const normalizeConfigValue = (value: string, type?: "text" | "number") => {
	if (type === "number") {
		const parsed = Number(value);
		return Number.isFinite(parsed) ? parsed : value;
	}
	return value;
};

const resetFormsFromConfig = (config: GuiConfig) => {
	const forms: Record<string, ApiRowForm> = {};
	for (const definition of apiRowDefs) {
		const node = getNode(config, definition.path);
		const values: Record<string, string> = {};
		for (const field of definition.fields) {
			const rawValue = node[field.key];
			values[field.key] =
				rawValue === null || rawValue === undefined ? "" : String(rawValue);
		}
		const secretKey = definition.secretKey ?? "api_key";
		forms[definition.provider] = {
			values,
			secret: "",
			configured: Boolean(node[`${secretKey}_configured`]),
			preview: String(node[`${secretKey}_preview`] ?? ""),
			testing: false,
			result: null,
		};
	}
	apiForms.value = forms;
};

const buildConfigPatch = () => {
	const patch: Record<string, unknown> = {};
	for (const definition of apiRowDefs) {
		const form = apiForms.value[definition.provider];
		if (!form) continue;
		for (const field of definition.fields) {
			setNodeValue(
				patch,
				definition.path,
				field.key,
				normalizeConfigValue(form.values[field.key] ?? "", field.type),
			);
		}
		if (definition.secretKey && form.secret.trim()) {
			setNodeValue(patch, definition.path, definition.secretKey, form.secret.trim());
		}
	}
	return patch;
};

const loadConfig = async () => {
	configLoading.value = true;
	configError.value = "";
	try {
		const response = await getGuiConfig();
		maskedConfig.value = response.data;
		resetFormsFromConfig(response.data);
	} catch (error) {
		console.error("加载 GUI 配置失败:", error);
		configError.value = "无法加载后端配置";
	} finally {
		configLoading.value = false;
	}
};

const saveConfig = async () => {
	configSaving.value = true;
	configError.value = "";
	try {
		const response = await saveGuiConfig(buildConfigPatch());
		maskedConfig.value = response.data;
		resetFormsFromConfig(response.data);
		toast({ title: "配置已保存", description: "真实密钥已写入本地 ignored JSON。" });
	} catch (error) {
		console.error("保存 GUI 配置失败:", error);
		configError.value = "保存配置失败";
		toast({
			title: "配置保存失败",
			description: "请检查后端服务是否运行。",
			variant: "destructive",
		});
	} finally {
		configSaving.value = false;
	}
};

const testProviderRow = async (definition: ApiRowDefinition) => {
	const form = apiForms.value[definition.provider];
	if (!form) return;
	form.testing = true;
	form.result = null;
	try {
		const response = await testGuiProvider({
			provider: definition.provider,
			config: buildConfigPatch(),
		});
		form.result = response.data;
		if (response.data.ok) {
			form.configured = true;
		}
	} catch (error) {
		console.error("测试 provider 失败:", error);
		form.result = {
			provider: definition.provider,
			ok: false,
			status: "request_failed",
			message: "测试请求失败，请确认后端服务正在运行。",
		};
	} finally {
		form.testing = false;
	}
};

const createWorkspace = async () => {
	workspaceCreating.value = true;
	try {
		const response = await createGuiWorkspace(workspaceTitle.value);
		activeTaskId.value = response.data.task_id;
		uploadStatus.value = {};
		progressEvents.value = [];
		eventCursor.value = 0;
		artifacts.value = [];
		artifactPreview.value = null;
		currentPlan.value = null;
		revisionRequests.value = [];
		toast({
			title: "工作区已创建",
			description: response.data.task_id,
		});
		await Promise.all([refreshChatMessages(), refreshRevisionRequests()]);
	} catch (error) {
		console.error("创建工作区失败:", error);
		toast({
			title: "创建工作区失败",
			description: "请确认后端服务正在运行。",
			variant: "destructive",
		});
	} finally {
		workspaceCreating.value = false;
	}
};

const chatRecordToLocalMessage = (record: ChatMessageRecord): LocalMessage => ({
	id: record.id,
	role: record.role,
	content: record.content,
	createdAt: record.created_at,
});

const refreshChatMessages = async () => {
	if (!activeTaskId.value) return;
	try {
		const response = await listChatMessages(activeTaskId.value);
		if (response.data.messages.length) {
			localMessages.value = response.data.messages.map(chatRecordToLocalMessage);
		}
	} catch (error) {
		console.error("读取对话消息失败:", error);
	}
};

const refreshRevisionRequests = async () => {
	if (!activeTaskId.value) return;
	try {
		const response = await listRevisionRequests(activeTaskId.value);
		revisionRequests.value = response.data.requests;
	} catch (error) {
		console.error("读取修订请求失败:", error);
	}
};

const planToText = (plan: WorkspacePlan) => {
	return [
		`Status: ${plan.status}`,
		`Problem: ${plan.problem_summary}`,
		"",
		"Data inventory:",
		...(plan.data_inventory.length ? plan.data_inventory.map((item) => `- ${item}`) : ["- No attachment files yet"]),
		"",
		"Modeling steps:",
		...plan.modeling_steps.map((step, index) => `${index + 1}. ${step}`),
		"",
		"Expected artifacts:",
		...plan.expected_artifacts.map((item) => `- ${item}`),
		"",
		"Risks:",
		...plan.risks.map((item) => `- ${item}`),
		plan.user_revision ? `\nUser revision:\n${plan.user_revision}` : "",
	].filter(Boolean).join("\n");
};

const ensureWorkspace = async () => {
	if (!activeTaskId.value) {
		await createWorkspace();
	}
	return activeTaskId.value;
};

const generatePlan = async () => {
	const taskId = await ensureWorkspace();
	if (!taskId) return;
	planningBusy.value = true;
	try {
		const response = await draftWorkspacePlan(taskId, problemText.value);
		currentPlan.value = response.data;
		planDraft.value = planToText(response.data);
		await refreshEvents();
	} catch (error) {
		console.error("生成计划失败:", error);
		toast({
			title: "生成计划失败",
			description: "请确认已创建工作区并填写题目文本。",
			variant: "destructive",
		});
	} finally {
		planningBusy.value = false;
	}
};

const applyPlanAction = async (
	action: "confirm" | "edit" | "regenerate" | "ask" | "skip" | "abort",
) => {
	const taskId = await ensureWorkspace();
	if (!taskId) return;
	planningBusy.value = true;
	try {
		let content = "";
		if (action === "edit") {
			content = planDraft.value;
		} else if (action === "ask") {
			content = chatInput.value.trim() || planDraft.value;
		} else if (action === "regenerate") {
			content = problemText.value;
		}
		const response = await applyWorkspacePlanAction(taskId, { action, content });
		currentPlan.value = response.data;
		planDraft.value = planToText(response.data);
		addLocalMessage("agent", `计划动作已记录：${action}`);
		if (action === "ask" && chatInput.value.trim()) {
			chatInput.value = "";
		}
		await refreshEvents();
	} catch (error) {
		console.error("计划动作失败:", error);
		toast({
			title: "计划动作失败",
			description: "请检查后端服务。",
			variant: "destructive",
		});
	} finally {
		planningBusy.value = false;
	}
};

const uploadFilesForKind = async (kind: WorkspaceFileKind, event: Event) => {
	const input = event.target as HTMLInputElement;
	const files = Array.from(input.files ?? []);
	if (!files.length || !activeTaskId.value) return;

	uploadingKind.value = kind;
	try {
		const response = await uploadWorkspaceFiles(activeTaskId.value, kind, files);
		uploadStatus.value = {
			...uploadStatus.value,
			[kind]: response.data.files,
		};
		toast({
			title: "上传完成",
			description: `${files.length} 个文件已写入 ${kind}`,
		});
	} catch (error) {
		console.error("上传文件失败:", error);
		toast({
			title: "上传失败",
			description: "请检查文件名和后端服务。",
			variant: "destructive",
		});
	} finally {
		uploadingKind.value = null;
		input.value = "";
	}
};

const refreshRagLibrary = async () => {
	ragLoading.value = true;
	try {
		const [casesResponse, guideResponse] = await Promise.all([
			listRagCases(),
			getRagGuide(),
		]);
		ragCases.value = casesResponse.data.cases;
		ragGuide.value = guideResponse.data;
	} catch (error) {
		console.error("读取 RAG 知识库失败:", error);
	} finally {
		ragLoading.value = false;
	}
};

const rebuildRagLibraryIndex = async () => {
	ragRebuilding.value = true;
	ragIndexMessage.value = "";
	try {
		const response = await rebuildRagIndex();
		ragIndexMessage.value = `索引已重建：${response.data.valid_case_count}/${response.data.case_count} 个有效案例`;
		await refreshRagLibrary();
	} catch (error) {
		console.error("重建 RAG 索引失败:", error);
		ragIndexMessage.value = "索引重建失败，请检查后端服务。";
	} finally {
		ragRebuilding.value = false;
	}
};

const addLocalMessage = (role: LocalMessage["role"], content: string) => {
	localMessages.value.push({
		role,
		content,
		createdAt: new Date().toISOString(),
	});
};

const pushPersistedMessage = (message: ChatMessageRecord) => {
	localMessages.value.push(chatRecordToLocalMessage(message));
};

const sendChatMessage = async () => {
	const content = chatInput.value.trim();
	if (!content) return;
	const taskId = await ensureWorkspace();
	if (!taskId) return;
	try {
		const userResponse = await appendChatMessage(taskId, {
			role: "user",
			content,
		});
		pushPersistedMessage(userResponse.data.message);
		const agentResponse = await appendChatMessage(taskId, {
			role: "agent",
			content: "收到。我会把这条意见纳入执行计划或后续修改请求。",
		});
		pushPersistedMessage(agentResponse.data.message);
		chatInput.value = "";
		await refreshEvents();
	} catch (error) {
		console.error("保存对话消息失败:", error);
		toast({
			title: "消息保存失败",
			description: "请确认后端服务正在运行。",
			variant: "destructive",
		});
	}
};

const refreshEvents = async () => {
	if (!activeTaskId.value) return;
	try {
		const response = await getWorkspaceEvents(activeTaskId.value, eventCursor.value);
		if (response.data.events.length) {
			progressEvents.value = [...progressEvents.value, ...response.data.events];
			eventCursor.value = response.data.next_after;
		}
	} catch (error) {
		console.error("读取进度事件失败:", error);
	}
};

const refreshArtifacts = async () => {
	if (!activeTaskId.value) return;
	try {
		const response = await listWorkspaceArtifacts(activeTaskId.value);
		artifacts.value = response.data.artifacts;
	} catch (error) {
		console.error("读取产物失败:", error);
	}
};

const startProgressPolling = () => {
	if (progressTimer) return;
	progressTimer = setInterval(() => {
		refreshEvents();
		refreshArtifacts();
	}, 2000);
};

const stopProgressPolling = () => {
	if (progressTimer) {
		clearInterval(progressTimer);
		progressTimer = null;
	}
};

const startRun = async () => {
	if (!activeTaskId.value) {
		await createWorkspace();
	}
	if (!activeTaskId.value) return;
	if (currentPlan.value?.status !== "approved") {
		toast({
			title: "计划尚未确认",
			description: "MVP 允许继续运行，但建议先确认执行计划。",
		});
	}
	running.value = true;
	try {
		await runWorkspace(activeTaskId.value, {
			problem_text: problemText.value,
			mode: "real",
			format_output: "Markdown",
		});
		addLocalMessage("agent", "任务已启动。我会持续读取后端进度事件。");
		await refreshEvents();
		startProgressPolling();
	} catch (error) {
		console.error("启动任务失败:", error);
		running.value = false;
		toast({
			title: "启动失败",
			description: "请确认已上传题目或填写题目文本，并检查后端服务。",
			variant: "destructive",
		});
	}
};

const stopRun = async () => {
	if (!activeTaskId.value) return;
	try {
		const response = await stopWorkspace(activeTaskId.value);
		running.value = false;
		stopProgressPolling();
		addLocalMessage("agent", response.data.message);
		await refreshEvents();
	} catch (error) {
		console.error("停止任务失败:", error);
	}
};

const requestResume = async () => {
	const taskId = await ensureWorkspace();
	if (!taskId) return;
	const instruction = chatInput.value.trim() || planDraft.value;
	if (!instruction.trim()) return;
	revisionBusy.value = true;
	try {
		const targetArtifacts = artifacts.value
			.filter((artifact) =>
				["md", "txt", "tex", "bib", "json", "csv", "log", "py"].includes(
					artifact.file_type,
				),
			)
			.map((artifact) => artifact.path);
		const revisionResponse = await createRevisionRequest(taskId, {
			instruction,
			target_artifacts: targetArtifacts,
		});
		revisionRequests.value = [
			...revisionRequests.value,
			revisionResponse.data.request,
		];
		const userResponse = await appendChatMessage(taskId, {
			role: "user",
			content: instruction,
		});
		pushPersistedMessage(userResponse.data.message);
		const response = await resumeWorkspace(taskId, instruction);
		const agentResponse = await appendChatMessage(taskId, {
			role: "agent",
			content: response.data.message,
		});
		pushPersistedMessage(agentResponse.data.message);
		chatInput.value = "";
		await refreshEvents();
	} catch (error) {
		console.error("发送修改请求失败:", error);
		toast({
			title: "修订请求失败",
			description: "请检查后端服务。",
			variant: "destructive",
		});
	} finally {
		revisionBusy.value = false;
	}
};

const openArtifact = async (artifact: ArtifactItem) => {
	if (!activeTaskId.value || !artifact.path || artifact.path.endsWith("/")) return;
	if (!["md", "txt", "tex", "bib", "json", "csv", "log", "py"].includes(artifact.file_type)) {
		window.open(getWorkspaceArtifactDownloadUrl(activeTaskId.value, artifact.path), "_blank");
		return;
	}
	artifactLoading.value = true;
	try {
		const response = await readWorkspaceArtifact(activeTaskId.value, artifact.path);
		artifactPreview.value = {
			path: response.data.path,
			content: response.data.content,
		};
	} catch (error) {
		console.error("读取产物失败:", error);
	} finally {
		artifactLoading.value = false;
	}
};

onMounted(() => {
	loadConfig();
	refreshRagLibrary();
});

onBeforeUnmount(() => {
	stopProgressPolling();
});
</script>

<template>
  <main class="min-h-screen bg-zinc-100 text-zinc-950">
    <header class="border-b border-zinc-800 bg-zinc-950 text-zinc-50">
      <div class="mx-auto flex max-w-[1800px] items-center justify-between gap-4 px-5 py-3">
        <div class="min-w-0">
          <div class="flex items-center gap-2 text-xs uppercase tracking-wide text-zinc-400">
            <Bot class="size-4" />
            GUI Studio
          </div>
          <div class="mt-1 flex flex-wrap items-center gap-3">
            <h1 class="text-xl font-semibold">{{ workspaceTitle }}</h1>
            <span class="rounded border border-zinc-700 px-2 py-0.5 font-mono text-xs text-zinc-300">
              {{ activeTaskId || "no-workspace" }}
            </span>
          </div>
        </div>
        <div class="flex shrink-0 items-center gap-2">
          <Button variant="secondary" size="sm" :disabled="workspaceCreating" @click="createWorkspace">
            <CheckCircle2 />
            {{ workspaceCreating ? "创建中" : "新建工作区" }}
          </Button>
          <Button size="sm" :disabled="running" @click="startRun">
            <Play />
            {{ running ? "运行中" : "开始运行" }}
          </Button>
          <Button variant="outline" size="sm" class="border-zinc-700 bg-zinc-950 text-zinc-50 hover:bg-zinc-900" @click="stopRun">
            <Square />
            停止
          </Button>
        </div>
      </div>
    </header>

    <div class="mx-auto grid max-w-[1800px] gap-4 px-5 py-4 xl:grid-cols-[360px_minmax(0,1fr)_420px]">
      <aside class="flex min-h-[calc(100vh-96px)] flex-col gap-4">
        <Tabs default-value="settings" class="flex min-h-0 flex-1 flex-col">
          <TabsList class="grid w-full grid-cols-2">
            <TabsTrigger value="settings">
              <Settings class="mr-2 size-4" />
              设置
            </TabsTrigger>
            <TabsTrigger value="rag">
              <BookOpen class="mr-2 size-4" />
              RAG
            </TabsTrigger>
          </TabsList>

          <TabsContent value="settings" class="mt-3 min-h-0 flex-1">
            <Card class="h-full rounded-lg shadow-sm">
              <CardHeader class="pb-3">
                <CardTitle class="text-base">API 配置</CardTitle>
                <CardDescription>每个 provider 都会有独立通断测试按钮。</CardDescription>
              </CardHeader>
              <CardContent>
                <ScrollArea class="h-[calc(100vh-220px)] pr-3">
                  <div class="mb-3 flex items-center justify-between gap-3">
                    <div class="text-xs text-zinc-500">
                      已配置 {{ configuredCount }} / {{ apiRowDefs.length }}
                    </div>
                    <Button size="xs" :disabled="configSaving || configLoading" @click="saveConfig">
                      {{ configSaving ? "保存中" : "保存配置" }}
                    </Button>
                  </div>
                  <p v-if="configError" class="mb-3 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">
                    {{ configError }}
                  </p>
                  <div v-if="configLoading" class="rounded-md border bg-white p-4 text-sm text-zinc-500">
                    正在加载配置...
                  </div>
                  <div v-else class="flex flex-col gap-3">
                    <div v-for="definition in apiRowDefs" :key="definition.provider" class="rounded-md border bg-white p-3">
                      <div class="mb-2 flex items-center justify-between gap-2">
                        <div class="min-w-0">
                          <div class="truncate text-sm font-medium">{{ definition.label }}</div>
                          <div class="font-mono text-[11px] text-zinc-500">{{ definition.provider }}</div>
                        </div>
                        <Button
                          variant="outline"
                          size="xs"
                          :disabled="apiForms[definition.provider]?.testing"
                          @click="testProviderRow(definition)"
                        >
                          {{ apiForms[definition.provider]?.testing ? "测试中" : "测试" }}
                        </Button>
                      </div>
                      <div class="grid gap-2">
                        <Input
                          v-if="definition.secretKey"
                          v-model="apiForms[definition.provider].secret"
                          :placeholder="apiForms[definition.provider].configured ? `已配置 ${apiForms[definition.provider].preview}` : 'API Key'"
                          type="password"
                        />
                        <label v-for="field in definition.fields" :key="field.key" class="grid gap-1">
                          <span class="text-[11px] text-zinc-500">{{ field.label }}</span>
                          <Input
                            v-model="apiForms[definition.provider].values[field.key]"
                            :type="field.type === 'number' ? 'number' : 'text'"
                            :placeholder="field.placeholder || field.label"
                          />
                        </label>
                      </div>
                      <p
                        class="mt-2 text-xs"
                        :class="{
                          'text-green-700': apiForms[definition.provider]?.result?.ok,
                          'text-red-700': apiForms[definition.provider]?.result && !apiForms[definition.provider]?.result?.ok,
                          'text-zinc-500': !apiForms[definition.provider]?.result,
                        }"
                      >
                        {{ apiForms[definition.provider]?.result?.message || (apiForms[definition.provider]?.configured ? `已保存 ${apiForms[definition.provider]?.preview}` : "未测试") }}
                      </p>
                    </div>
                  </div>
                </ScrollArea>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="rag" class="mt-3 min-h-0 flex-1">
            <Card class="h-full rounded-lg shadow-sm">
              <CardHeader class="pb-3">
                <CardTitle class="text-base">范文知识库</CardTitle>
                <CardDescription>初始为空目录，等待用户按案例填充。</CardDescription>
              </CardHeader>
              <CardContent class="text-sm">
                <div class="rounded-md border bg-white p-3 font-mono text-xs leading-6">
                  {{ ragGuide?.root || ragKnowledgeDir }}/<br>
                  <template v-for="line in (ragGuide?.example || ['case-id/', '  problem.pdf', '  paper.pdf', '  data/', '  notes.md'])" :key="line">
                    {{ line }}<br>
                  </template>
                </div>
                <div class="mt-3 flex items-center gap-2">
                  <Button size="xs" variant="outline" :disabled="ragLoading" @click="refreshRagLibrary">
                    {{ ragLoading ? "扫描中" : "扫描案例" }}
                  </Button>
                  <Button size="xs" :disabled="ragRebuilding" @click="rebuildRagLibraryIndex">
                    {{ ragRebuilding ? "重建中" : "重建索引" }}
                  </Button>
                </div>
                <p v-if="ragIndexMessage" class="mt-2 rounded-md border bg-zinc-50 px-3 py-2 text-xs text-zinc-700">
                  {{ ragIndexMessage }}
                </p>
                <div class="mt-3 flex flex-col gap-2">
                  <div v-if="!ragCases.length" class="rounded-md border bg-white p-3 text-zinc-500">
                    当前没有用户导入的范文案例。
                  </div>
                  <div v-for="item in ragCases" :key="item.case_id" class="rounded-md border bg-white p-3">
                    <div class="flex items-center justify-between gap-2">
                      <div class="font-mono text-sm">{{ item.case_id }}</div>
                      <span
                        class="rounded border px-2 py-0.5 text-[11px]"
                        :class="item.status === 'valid' ? 'border-green-200 bg-green-50 text-green-700' : 'border-red-200 bg-red-50 text-red-700'"
                      >
                        {{ item.status }}
                      </span>
                    </div>
                    <div class="mt-1 text-xs text-zinc-500">{{ item.files.length }} files</div>
                    <ul v-if="item.issues.length" class="mt-2 list-inside list-disc text-xs text-red-700">
                      <li v-for="issue in item.issues" :key="issue">{{ issue }}</li>
                    </ul>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </aside>

      <section class="flex min-h-[calc(100vh-96px)] min-w-0 flex-col gap-4">
        <Card class="rounded-lg shadow-sm">
          <CardHeader class="pb-3">
            <CardTitle class="flex items-center gap-2 text-base">
              <UploadCloud class="size-4" />
              本次题目上传
            </CardTitle>
            <CardDescription>赛题、附件、格式样例和额外要求分开上传。</CardDescription>
          </CardHeader>
          <CardContent>
            <div v-if="!activeTaskId" class="mb-3 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
              请先创建工作区，再上传本次题目文件。
            </div>
            <div class="grid gap-3 md:grid-cols-5">
              <label
                v-for="item in uploadKinds"
                :key="item.key"
                class="flex cursor-pointer flex-col gap-2 rounded-md border bg-white p-3 transition-colors hover:bg-zinc-50"
                :class="{ 'cursor-not-allowed opacity-60': !activeTaskId || uploadingKind === item.key }"
              >
                <component :is="item.icon" class="size-5 text-zinc-700" />
                <span class="text-sm font-medium">{{ item.label }}</span>
                <span class="text-xs text-zinc-500">
                  {{ uploadingKind === item.key ? "上传中" : uploadStatus[item.key]?.length ? `${uploadStatus[item.key].length} 个文件` : "选择文件" }}
                </span>
                <input
                  class="text-xs"
                  type="file"
                  multiple
                  :disabled="!activeTaskId || uploadingKind === item.key"
                  @change="uploadFilesForKind(item.key, $event)"
                >
              </label>
            </div>
            <Textarea v-model="problemText" class="mt-3 min-h-24" placeholder="也可以直接粘贴题目文本或补充要求。" />
          </CardContent>
        </Card>

        <div class="grid min-h-0 flex-1 gap-4 lg:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
          <Card class="min-h-0 rounded-lg shadow-sm">
            <CardHeader class="pb-3">
              <CardTitle class="flex items-center gap-2 text-base">
                <MessageSquare class="size-4" />
                对话区
              </CardTitle>
              <CardDescription>用户和 Agent 讨论方案、修改意见和审稿反馈。</CardDescription>
            </CardHeader>
            <CardContent class="flex h-[420px] flex-col gap-3">
              <ScrollArea class="min-h-0 flex-1 rounded-md border bg-white p-3">
                <div class="flex flex-col gap-3">
                  <div
                    v-for="message in localMessages"
                    :key="message.createdAt + message.content"
                    class="max-w-[88%] rounded-md border px-3 py-2 text-sm"
                    :class="message.role === 'user' ? 'ml-auto bg-zinc-950 text-zinc-50' : 'bg-zinc-50 text-zinc-800'"
                  >
                    <div class="mb-1 text-[11px] opacity-70">{{ message.role === "user" ? "User" : "Agent" }}</div>
                    <div class="whitespace-pre-wrap">{{ message.content }}</div>
                  </div>
                </div>
              </ScrollArea>
              <div v-if="latestRevisionRequest" class="rounded-md border bg-zinc-50 px-3 py-2 text-xs text-zinc-600">
                最新修订：
                <span class="font-mono">{{ latestRevisionRequest.status }}</span>
                <span class="ml-2">{{ latestRevisionRequest.instruction.slice(0, 96) }}</span>
              </div>
              <div class="flex gap-2">
                <Input v-model="chatInput" placeholder="输入你的想法、约束或修改意见" />
                <Button @click="sendChatMessage">发送</Button>
                <Button variant="outline" :disabled="revisionBusy" @click="requestResume">
                  {{ revisionBusy ? "记录中" : "修改" }}
                </Button>
              </div>
            </CardContent>
          </Card>

          <Card class="min-h-0 rounded-lg shadow-sm">
            <CardHeader class="pb-3">
              <div class="flex flex-wrap items-center justify-between gap-2">
                <CardTitle class="flex items-center gap-2 text-base">
                  <Activity class="size-4" />
                  执行计划
                </CardTitle>
                <span class="rounded border px-2 py-0.5 font-mono text-[11px]"
                  :class="{
                    'border-green-200 bg-green-50 text-green-700': currentPlan?.status === 'approved',
                    'border-amber-200 bg-amber-50 text-amber-700': currentPlan?.status === 'draft',
                    'border-red-200 bg-red-50 text-red-700': currentPlan?.status === 'aborted',
                    'border-zinc-200 bg-zinc-50 text-zinc-600': !currentPlan || currentPlan?.status === 'skipped',
                  }"
                >
                  {{ currentPlan?.status || "not-generated" }}
                </span>
              </div>
              <CardDescription>由 Agent 主导生成，用户确认或修改后运行。</CardDescription>
            </CardHeader>
            <CardContent class="flex h-[452px] flex-col gap-3">
              <div class="grid gap-2 sm:grid-cols-4">
                <Button size="xs" :disabled="planningBusy" @click="generatePlan">
                  <RefreshCw />
                  {{ planningBusy ? "处理中" : "生成计划" }}
                </Button>
                <Button size="xs" variant="outline" :disabled="planningBusy || !currentPlan" @click="applyPlanAction('confirm')">
                  <CheckCircle2 />
                  确认
                </Button>
                <Button size="xs" variant="outline" :disabled="planningBusy || !currentPlan" @click="applyPlanAction('edit')">
                  <Save />
                  保存修改
                </Button>
                <Button size="xs" variant="outline" :disabled="planningBusy || !currentPlan" @click="applyPlanAction('regenerate')">
                  <RefreshCw />
                  重新生成
                </Button>
                <Button size="xs" variant="outline" :disabled="planningBusy || !currentPlan" @click="applyPlanAction('ask')">
                  <HelpCircle />
                  提问
                </Button>
                <Button size="xs" variant="outline" :disabled="planningBusy || !currentPlan" @click="applyPlanAction('skip')">
                  <SkipForward />
                  跳过
                </Button>
                <Button size="xs" variant="outline" class="border-red-200 text-red-700 hover:bg-red-50" :disabled="planningBusy || !currentPlan" @click="applyPlanAction('abort')">
                  <Ban />
                  中止
                </Button>
              </div>
              <div v-if="currentPlan?.last_action" class="rounded-md border bg-white px-3 py-2 text-xs text-zinc-600">
                上次动作：
                <span class="font-mono">{{ currentPlan.last_action.action }}</span>
                <span v-if="currentPlan.last_action.content" class="ml-2 text-zinc-500">
                  {{ currentPlan.last_action.content.slice(0, 80) }}
                </span>
              </div>
              <Textarea v-model="planDraft" class="min-h-0 flex-1 font-mono text-sm" />
            </CardContent>
          </Card>
        </div>
      </section>

      <aside class="flex min-h-[calc(100vh-96px)] flex-col gap-4">
        <Card class="min-h-0 flex-1 rounded-lg shadow-sm">
          <CardHeader class="pb-3">
            <CardTitle class="text-base">Agent 进度</CardTitle>
            <CardDescription>运行时持续显示后端事件，避免用户误以为卡住。</CardDescription>
          </CardHeader>
          <CardContent>
            <div class="flex flex-col gap-3">
              <div v-for="item in displayedProgressEvents" :key="`${item.seq}-${item.stage}`" class="rounded-md border bg-white p-3">
                <div class="flex items-center justify-between gap-2">
                  <div class="font-mono text-xs text-zinc-500">{{ item.stage }}</div>
                  <span
                    class="rounded border px-2 py-0.5 text-[11px]"
                    :class="{
                      'border-green-200 bg-green-50 text-green-700': item.level === 'success',
                      'border-red-200 bg-red-50 text-red-700': item.level === 'error',
                      'border-amber-200 bg-amber-50 text-amber-700': item.level === 'warning',
                      'border-zinc-200 bg-zinc-50 text-zinc-600': item.level === 'info',
                    }"
                  >
                    {{ item.level }}
                  </span>
                </div>
                <div class="mt-1 text-sm">{{ item.message }}</div>
                <div v-if="item.timestamp" class="mt-2 font-mono text-[11px] text-zinc-400">
                  {{ new Date(item.timestamp).toLocaleTimeString() }}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card class="min-h-0 flex-1 rounded-lg shadow-sm">
          <CardHeader class="pb-3">
            <CardTitle class="text-base">产物</CardTitle>
            <CardDescription>论文、图表、数据表和日志会在这里预览。</CardDescription>
          </CardHeader>
          <CardContent>
            <div class="flex flex-col gap-2">
              <button
                v-for="item in displayedArtifacts"
                :key="item.path"
                type="button"
                class="flex items-center justify-between gap-3 rounded-md border bg-white p-3 text-left transition-colors hover:bg-zinc-50"
                :disabled="!artifacts.length"
                @click="openArtifact(item)"
              >
                <div class="min-w-0">
                  <div class="truncate font-mono text-sm">{{ item.path }}</div>
                  <div class="text-xs text-zinc-500">{{ item.file_type }} · {{ item.size }} bytes</div>
                </div>
                <span class="shrink-0 rounded border px-2 py-0.5 text-xs text-zinc-600">{{ artifacts.length ? "打开" : "待生成" }}</span>
              </button>
            </div>
            <div class="mt-3 rounded-md border bg-zinc-950 p-3 text-zinc-50">
              <div class="mb-2 flex items-center justify-between gap-2">
                <span class="font-mono text-xs text-zinc-400">{{ artifactPreview?.path || "preview" }}</span>
                <span class="text-xs text-zinc-500">{{ artifactLoading ? "读取中" : "" }}</span>
              </div>
              <pre class="max-h-64 overflow-auto whitespace-pre-wrap text-xs leading-5">{{ artifactPreview?.content || "选择文本产物后预览内容。" }}</pre>
            </div>
          </CardContent>
        </Card>
      </aside>
    </div>
  </main>
</template>
