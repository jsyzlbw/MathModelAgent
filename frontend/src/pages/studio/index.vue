<script setup lang="ts">
import {
	type GuiConfig,
	type ProviderTestResponse,
	getGuiConfig,
	saveGuiConfig,
	testGuiProvider,
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
	BookOpen,
	Bot,
	CheckCircle2,
	Database,
	FileUp,
	MessageSquare,
	Play,
	Settings,
	Square,
	UploadCloud,
} from "lucide-vue-next";
import { computed, onMounted, ref } from "vue";

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

const { toast } = useToast();

const activeTaskId = ref("");
const workspaceTitle = ref("MCM/ICM Workspace");
const planDraft = ref(
	"1. 理解题意并拆解子问题\n2. 讨论候选模型和数据需求\n3. 生成代码实验与图表\n4. 写作论文并进行审稿修订",
);
const chatInput = ref("");
const problemText = ref("");

const progressItems = [
	{ stage: "workspace.created", message: "等待创建工作区", tone: "muted" },
	{ stage: "config.pending", message: "等待配置 API 并测试通断", tone: "muted" },
	{ stage: "plan.pending", message: "等待用户与 Agent 确认执行方案", tone: "muted" },
];

const artifactItems = [
	{ path: "res.md", type: "markdown", status: "待生成" },
	{ path: "res.pdf", type: "pdf", status: "待生成" },
	{ path: "figures/", type: "folder", status: "待生成" },
];

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

const configuredCount = computed(
	() => Object.values(apiForms.value).filter((form) => form.configured).length,
);

const uploadKinds = [
	{ key: "problem", label: "赛题文件", icon: FileUp },
	{ key: "attachment", label: "题目附件", icon: Database },
	{ key: "template", label: "格式样例", icon: Archive },
	{ key: "requirement", label: "其他要求", icon: UploadCloud },
];

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

onMounted(() => {
	loadConfig();
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
          <Button variant="secondary" size="sm">
            <CheckCircle2 />
            新建工作区
          </Button>
          <Button size="sm">
            <Play />
            开始运行
          </Button>
          <Button variant="outline" size="sm" class="border-zinc-700 bg-zinc-950 text-zinc-50 hover:bg-zinc-900">
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
                  data/rag_cases/<br>
                  &nbsp;&nbsp;case-name/<br>
                  &nbsp;&nbsp;&nbsp;&nbsp;problem.pdf<br>
                  &nbsp;&nbsp;&nbsp;&nbsp;data/<br>
                  &nbsp;&nbsp;&nbsp;&nbsp;paper.pdf<br>
                  &nbsp;&nbsp;&nbsp;&nbsp;notes.md
                </div>
                <p class="mt-3 text-zinc-600">
                  后续路线会加入结构校验、索引构建和检索引用。当前界面先固定用户导入规范。
                </p>
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
            <div class="grid gap-3 md:grid-cols-4">
              <label v-for="item in uploadKinds" :key="item.key" class="flex cursor-pointer flex-col gap-2 rounded-md border bg-white p-3 transition-colors hover:bg-zinc-50">
                <component :is="item.icon" class="size-5 text-zinc-700" />
                <span class="text-sm font-medium">{{ item.label }}</span>
                <input class="text-xs" type="file" multiple>
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
                <div class="text-sm text-zinc-500">暂无消息。创建工作区后，可以从这里开始讨论计划。</div>
              </ScrollArea>
              <div class="flex gap-2">
                <Input v-model="chatInput" placeholder="输入你的想法、约束或修改意见" />
                <Button>发送</Button>
              </div>
            </CardContent>
          </Card>

          <Card class="min-h-0 rounded-lg shadow-sm">
            <CardHeader class="pb-3">
              <CardTitle class="flex items-center gap-2 text-base">
                <Activity class="size-4" />
                执行计划
              </CardTitle>
              <CardDescription>由 Agent 主导生成，用户确认或修改后运行。</CardDescription>
            </CardHeader>
            <CardContent>
              <Textarea v-model="planDraft" class="h-[420px] font-mono text-sm" />
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
              <div v-for="item in progressItems" :key="item.stage" class="rounded-md border bg-white p-3">
                <div class="font-mono text-xs text-zinc-500">{{ item.stage }}</div>
                <div class="mt-1 text-sm">{{ item.message }}</div>
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
              <div v-for="item in artifactItems" :key="item.path" class="flex items-center justify-between gap-3 rounded-md border bg-white p-3">
                <div class="min-w-0">
                  <div class="truncate font-mono text-sm">{{ item.path }}</div>
                  <div class="text-xs text-zinc-500">{{ item.type }}</div>
                </div>
                <span class="shrink-0 rounded border px-2 py-0.5 text-xs text-zinc-600">{{ item.status }}</span>
              </div>
            </div>
          </CardContent>
        </Card>
      </aside>
    </div>
  </main>
</template>
