import request from "@/utils/request";

export type GuiConfig = Record<string, unknown>;

export interface ProviderTestRequest {
	provider: string;
	config?: GuiConfig;
	dry_run?: boolean;
}

export interface ProviderTestResponse {
	provider: string;
	ok: boolean;
	status: string;
	message: string;
}

export interface WorkspaceResponse {
	task_id: string;
	status: string;
	title?: string;
}

export interface UploadedWorkspaceFile {
	kind: WorkspaceFileKind;
	filename: string;
	path: string;
	size: number;
}

export interface WorkspaceInputItem {
	kind: WorkspaceFileKind;
	path: string;
	filename: string;
	suffix: string;
	category: string;
	size: number;
	sha256: string;
	preview: string;
}

export interface WorkspaceInputManifest {
	version: number;
	generated_at: string;
	items: WorkspaceInputItem[];
}

export type WorkspaceFileKind =
	| "problem"
	| "attachment"
	| "template"
	| "requirement"
	| "chat";

export interface ProgressEvent {
	seq: number;
	timestamp: string;
	level: "info" | "warning" | "success" | "error" | string;
	stage: string;
	message: string;
	metadata: Record<string, unknown>;
}

export interface ArtifactItem {
	path: string;
	filename: string;
	size: number;
	file_type: string;
}

export interface RunWorkspacePayload {
	problem_text?: string;
	mode?: "demo" | "real";
	comp_template?: string;
	format_output?: string;
}

export interface ArtifactContentResponse {
	task_id: string;
	path: string;
	content: string;
}

export interface RagCaseFile {
	path: string;
	size: number;
	sha256: string;
}

export interface RagCaseItem {
	case_id: string;
	status: "valid" | "invalid" | string;
	issues: string[];
	files: RagCaseFile[];
}

export interface RagGuideResponse {
	root: string;
	required_files: string[];
	accepted_suffixes: string[];
	optional_paths: string[];
	example: string[];
}

export interface WorkspacePlan {
	version: number;
	status: "draft" | "approved" | "skipped" | "aborted" | string;
	created_at: string;
	updated_at: string;
	problem_summary: string;
	data_inventory: string[];
	modeling_steps: string[];
	expected_artifacts: string[];
	risks: string[];
	user_revision: string;
	user_question?: string;
	last_action: {
		action: string;
		content: string;
		created_at: string;
	} | null;
}

export interface PlanActionPayload {
	action: "confirm" | "edit" | "regenerate" | "ask" | "skip" | "abort";
	content?: string;
}

export interface ChatMessageRecord {
	id: string;
	role: "user" | "agent";
	content: string;
	attachments: string[];
	created_at: string;
}

export interface RevisionRequestRecord {
	id: string;
	instruction: string;
	target_artifacts: string[];
	status: string;
	created_at: string;
}

export function getGuiConfig() {
	return request.get<GuiConfig>("/api/gui/config");
}

export function saveGuiConfig(config: GuiConfig) {
	return request.put<GuiConfig>("/api/gui/config", config);
}

export function testGuiProvider(payload: ProviderTestRequest) {
	return request.post<ProviderTestResponse>(
		"/api/gui/config/test-provider",
		payload,
	);
}

export function createGuiWorkspace(title: string) {
	return request.post<WorkspaceResponse>("/api/gui/workspaces", { title });
}

export function uploadWorkspaceFiles(
	taskId: string,
	kind: WorkspaceFileKind,
	files: File[],
) {
	const formData = new FormData();
	for (const file of files) {
		formData.append("files", file);
	}
	return request.post<{
		task_id: string;
		files: UploadedWorkspaceFile[];
		manifest?: WorkspaceInputManifest;
	}>(`/api/gui/workspaces/${taskId}/files`, formData, {
		params: { kind },
		headers: { "Content-Type": "multipart/form-data" },
	});
}

export function listWorkspaceInputs(taskId: string) {
	return request.get<{
		task_id: string;
		manifest: WorkspaceInputManifest;
	}>(`/api/gui/workspaces/${taskId}/inputs`);
}

export function previewWorkspaceInput(taskId: string, path: string) {
	return request.get<{
		task_id: string;
		item: WorkspaceInputItem;
	}>(`/api/gui/workspaces/${taskId}/inputs/preview`, {
		params: { path },
	});
}

export function runWorkspace(taskId: string, payload: RunWorkspacePayload) {
	return request.post<WorkspaceResponse>(
		`/api/gui/workspaces/${taskId}/run`,
		payload,
		{ timeout: 30000 },
	);
}

export function stopWorkspace(taskId: string) {
	return request.post<{ success: boolean; message: string }>(
		`/api/gui/workspaces/${taskId}/stop`,
	);
}

export function resumeWorkspace(taskId: string, instruction: string) {
	return request.post<{
		task_id: string;
		status: string;
		message: string;
	}>(`/api/gui/workspaces/${taskId}/resume`, { instruction });
}

export function getWorkspaceEvents(taskId: string, after = 0) {
	return request.get<{
		task_id: string;
		events: ProgressEvent[];
		next_after: number;
	}>(`/api/gui/workspaces/${taskId}/events`, {
		params: { after },
	});
}

export function listWorkspaceArtifacts(taskId: string) {
	return request.get<{
		task_id: string;
		artifacts: ArtifactItem[];
	}>(`/api/gui/workspaces/${taskId}/artifacts`);
}

export function readWorkspaceArtifact(taskId: string, path: string) {
	return request.get<ArtifactContentResponse>(
		`/api/gui/workspaces/${taskId}/artifacts/content`,
		{ params: { path } },
	);
}

export function getWorkspaceArtifactDownloadUrl(taskId: string, path: string) {
	const baseURL = request.defaults.baseURL || "";
	const params = new URLSearchParams({ path });
	return `${baseURL}/api/gui/workspaces/${taskId}/artifacts/download?${params.toString()}`;
}

export function listRagCases() {
	return request.get<{
		root: string;
		cases: RagCaseItem[];
		manifest_path: string;
		index_path: string;
	}>("/api/gui/rag/cases");
}

export function validateRagCase(caseId: string) {
	return request.post<RagCaseItem>(`/api/gui/rag/cases/${caseId}/validate`);
}

export function rebuildRagIndex() {
	return request.post<{
		version: number;
		generated_at: string;
		case_count: number;
		valid_case_count: number;
		manifest_path: string;
		index_path: string;
	}>("/api/gui/rag/index/rebuild");
}

export function getRagGuide() {
	return request.get<RagGuideResponse>("/api/gui/rag/guide");
}

export function draftWorkspacePlan(taskId: string, problemText = "") {
	return request.post<WorkspacePlan>(
		`/api/gui/workspaces/${taskId}/planning/draft`,
		{ problem_text: problemText },
	);
}

export function getWorkspacePlan(taskId: string) {
	return request.get<WorkspacePlan>(`/api/gui/workspaces/${taskId}/planning`);
}

export function applyWorkspacePlanAction(
	taskId: string,
	payload: PlanActionPayload,
) {
	return request.post<WorkspacePlan>(
		`/api/gui/workspaces/${taskId}/planning/action`,
		{
			action: payload.action,
			content: payload.content ?? "",
		},
	);
}

export function listChatMessages(taskId: string) {
	return request.get<{
		task_id: string;
		messages: ChatMessageRecord[];
	}>(`/api/gui/workspaces/${taskId}/chat/messages`);
}

export function appendChatMessage(
	taskId: string,
	payload: {
		role: "user" | "agent";
		content: string;
		attachments?: string[];
	},
) {
	return request.post<{
		task_id: string;
		message: ChatMessageRecord;
	}>(`/api/gui/workspaces/${taskId}/chat/messages`, {
		role: payload.role,
		content: payload.content,
		attachments: payload.attachments ?? [],
	});
}

export function listRevisionRequests(taskId: string) {
	return request.get<{
		task_id: string;
		requests: RevisionRequestRecord[];
	}>(`/api/gui/workspaces/${taskId}/revision/requests`);
}

export function createRevisionRequest(
	taskId: string,
	payload: {
		instruction: string;
		target_artifacts?: string[];
	},
) {
	return request.post<{
		task_id: string;
		request: RevisionRequestRecord;
	}>(`/api/gui/workspaces/${taskId}/revision/requests`, {
		instruction: payload.instruction,
		target_artifacts: payload.target_artifacts ?? [],
	});
}
