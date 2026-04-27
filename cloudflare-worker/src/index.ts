export interface Env {
  DB: D1Database;
  ADMIN_TOKEN: string;
  CLIENT_KEY?: string;
  RUNS_LIMITER: RateLimit;
}

type JsonObject = Record<string, unknown>;

const MAX_RUN_BODY_BYTES = 16 * 1024;
const MAX_HIT_IDS = 500;
const MAX_QUIZ_ANSWERS = 200;
const MAX_EXPORTED_QUIZ_QUESTION_COLUMNS = 25;
const MAX_EMAIL_CHARS = 320;
const MAX_PLAYER_FIELD_CHARS = 200;
const MAX_QUIZ_TEXT_CHARS = 500;
const MAX_QUIZ_ANSWER_TEXT_CHARS = 300;
const EMAIL_RE = /^[A-Z0-9.!#$%&'*+/=?^_`{|}~-]{1,64}@[A-Z0-9-]{1,63}(?:\.[A-Z0-9-]{1,63})+$/i;
const SECURITY_HEADERS: Record<string, string> = {
  "X-Content-Type-Options": "nosniff",
  "Referrer-Policy": "no-referrer",
};

function jsonResponse(status: number, payload: JsonObject): Response {
  return new Response(JSON.stringify(payload), {
    status,
    headers: {
      ...SECURITY_HEADERS,
      "Content-Type": "application/json; charset=utf-8",
      "Cache-Control": "no-store",
    },
  });
}

function csvResponse(filename: string, csvBody: string): Response {
  return new Response(`\uFEFF${csvBody}`, {
    status: 200,
    headers: {
      ...SECURITY_HEADERS,
      "Content-Type": "text/csv; charset=utf-8",
      "Content-Disposition": `attachment; filename="${filename}"`,
      "Cache-Control": "no-store",
    },
  });
}

function unauthorized(message = "Unauthorized"): Response {
  return jsonResponse(401, { ok: false, error: message });
}

function badRequest(message: string): Response {
  return jsonResponse(400, { ok: false, error: message });
}

function serverError(): Response {
  return jsonResponse(500, { ok: false, error: "Server error." });
}

function parseIdSegment(pathname: string, suffix: string): number | null {
  const escaped = suffix.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const re = new RegExp(`^/api/v1/dev/players/(\\d+)/${escaped}$`);
  const match = pathname.match(re);
  if (!match) {
    return null;
  }
  return Number.parseInt(match[1], 10);
}

function isJsonObject(value: unknown): value is JsonObject {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function timingSafeEqual(a: string, b: string): boolean {
  if (a.length !== b.length) {
    return false;
  }
  let diff = 0;
  for (let i = 0; i < a.length; i++) {
    diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  }
  return diff === 0;
}

function isAdminAuthorized(req: Request, env: Env): boolean {
  const auth = req.headers.get("Authorization") ?? "";
  const token = auth.startsWith("Bearer ") ? auth.slice(7) : "";
  if (!env.ADMIN_TOKEN || !token) {
    return false;
  }
  return timingSafeEqual(token, env.ADMIN_TOKEN);
}

function isClientAuthorized(req: Request, env: Env): boolean {
  const expectedKey = env.CLIENT_KEY?.trim();
  if (!expectedKey) return false;
  const key = req.headers.get("X-Client-Key") ?? "";
  if (!key) {
    return false;
  }
  return timingSafeEqual(key, expectedKey);
}

async function isRunUploadAllowed(req: Request, env: Env): Promise<boolean> {
  const ip = (req.headers.get("CF-Connecting-IP") ?? "").trim() || "unknown";
  const { success } = await env.RUNS_LIMITER.limit({ key: ip });
  return success;
}

function toIsoStringOrNow(value: unknown): string {
  if (typeof value !== "string" || value.trim() === "") {
    return new Date().toISOString();
  }
  const parsed = Date.parse(value);
  if (Number.isNaN(parsed)) {
    return new Date().toISOString();
  }
  return new Date(parsed).toISOString();
}

function toNumber(value: unknown, fallback = 0): number {
  const n = Number(value);
  return Number.isFinite(n) ? n : fallback;
}

function toInteger(value: unknown, fallback = 0): number {
  const n = Number.parseInt(String(value), 10);
  return Number.isFinite(n) ? n : fallback;
}

function toNonNegativeInteger(value: unknown, fallback = 0): number {
  return Math.max(0, toInteger(value, fallback));
}

function trimString(value: unknown, maxLength: number): string {
  return String(value ?? "").trim().slice(0, maxLength);
}

function normalizeEmail(value: unknown): string | null {
  const email = trimString(value, MAX_EMAIL_CHARS).toLowerCase();
  if (!EMAIL_RE.test(email)) {
    return null;
  }

  const [local, domain] = email.split("@");
  if (!local || !domain || local.length > 64 || domain.length > 255) {
    return null;
  }

  const labels = domain.split(".");
  if (labels.some((label) => label === "" || label.startsWith("-") || label.endsWith("-"))) {
    return null;
  }
  return email;
}

function toStringList(value: unknown, maxItems: number): string[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value
    .slice(0, maxItems)
    .map((item) => trimString(item, 256))
    .filter((item) => item !== "");
}

function csvSafeCell(value: unknown): string {
  let text = value == null ? "" : String(value);
  if (text.length > 0 && ["=", "+", "-", "@"].includes(text[0])) {
    text = `'${text}`;
  }
  if (text.includes('"')) {
    text = text.replaceAll('"', '""');
  }
  if (/[",\r\n]/.test(text)) {
    return `"${text}"`;
  }
  return text;
}

function formatQuizAnswers(rawJson: string): string {
  try {
    const answers = JSON.parse(rawJson) as Array<{
      question_order?: number;
      question_text?: string;
      selected_text?: string;
      correct_text?: string;
      is_correct?: boolean;
    }>;
    if (!Array.isArray(answers) || answers.length === 0) return "";
    return answers
      .map((a) => {
        const result = a.is_correct
          ? "Correct"
          : `Wrong (correct answer: "${a.correct_text ?? ""}")`;
        return `Q${a.question_order ?? "?"}: "${a.question_text ?? ""}" — Player answered: "${a.selected_text ?? ""}" — ${result}`;
      })
      .join(" | ");
  } catch {
    return rawJson;
  }
}

type QuizAnswer = {
  question_order?: number;
  question_text?: string;
  selected_text?: string;
  correct_text?: string;
  is_correct?: boolean;
};

type StoredQuizAnswer = {
  question_order: number;
  question_text: string;
  selected_index: number;
  selected_text: string;
  correct_index: number;
  correct_text: string;
  is_correct: boolean;
};

function normalizeQuizAnswers(value: unknown): StoredQuizAnswer[] {
  if (!Array.isArray(value)) {
    return [];
  }

  return value.slice(0, MAX_QUIZ_ANSWERS).map((item, index) => {
    const answer: JsonObject = isJsonObject(item) ? item : {};
    return {
      question_order: toNonNegativeInteger(answer.question_order, index + 1),
      question_text: trimString(answer.question_text, MAX_QUIZ_TEXT_CHARS),
      selected_index: toInteger(answer.selected_index, -1),
      selected_text: trimString(answer.selected_text, MAX_QUIZ_ANSWER_TEXT_CHARS),
      correct_index: toInteger(answer.correct_index, -1),
      correct_text: trimString(answer.correct_text, MAX_QUIZ_ANSWER_TEXT_CHARS),
      is_correct: answer.is_correct === true,
    };
  });
}

function parseQuizAnswers(rawJson: string): QuizAnswer[] {
  try {
    const answers = JSON.parse(rawJson || "[]") as unknown;
    if (!Array.isArray(answers)) return [];
    return answers.filter((answer): answer is QuizAnswer => {
      return answer !== null && typeof answer === "object" && !Array.isArray(answer);
    });
  } catch {
    return [];
  }
}

function formatAnswerText(value: unknown): string {
  const text = value == null ? "" : String(value).trim();
  return text === "" ? "-" : text;
}

function formatQuizAnswerSummary(answers: QuizAnswer[]): string {
  if (answers.length === 0) {
    return "No quiz answers recorded.";
  }

  return answers
    .map((answer, index) => {
      const order = answer.question_order ?? index + 1;
      const question = formatAnswerText(answer.question_text);
      const selected = formatAnswerText(answer.selected_text);
      const correct = formatAnswerText(answer.correct_text);
      const result = answer.is_correct ? "Correct" : `Incorrect; correct answer: ${correct}`;
      return `Q${order}: ${question} - Player answered: ${selected} - ${result}`;
    })
    .join(" | ");
}

function quizAnswerCells(answers: QuizAnswer[], maxAnswers: number): string[] {
  const cells: string[] = [];
  for (let index = 0; index < maxAnswers; index++) {
    const answer = answers[index] ?? {};
    cells.push(
      formatAnswerText(answer.question_text),
      formatAnswerText(answer.selected_text),
      formatAnswerText(answer.correct_text),
      answer.is_correct === true ? "Correct" : answer.is_correct === false ? "Incorrect" : "-"
    );
  }
  return cells;
}

function toCsv(rows: unknown[][]): string {
  return rows
    .map((row) => row.map((value) => csvSafeCell(value)).join(","))
    .join("\n");
}

async function upsertPlayerAndGetId(
  env: Env,
  playerName: string,
  playerUsername: string,
  playerEmail: string
): Promise<number> {
  await env.DB.prepare(
    `
      INSERT INTO players (display_name, username, email)
      VALUES (?1, ?2, ?3)
      ON CONFLICT(email) DO UPDATE SET
        display_name = excluded.display_name,
        username = excluded.username,
        updated_at = CURRENT_TIMESTAMP
    `
  )
    .bind(playerName, playerUsername, playerEmail)
    .run();

  const row = await env.DB.prepare("SELECT id FROM players WHERE email = ?1")
    .bind(playerEmail)
    .first<{ id: number }>();

  if (!row || typeof row.id !== "number") {
    throw new Error("Failed to resolve player id.");
  }
  return row.id;
}

async function handleCreateRun(req: Request, env: Env): Promise<Response> {
  if (!isClientAuthorized(req, env)) {
    return unauthorized("Invalid client key.");
  }

  if (!(await isRunUploadAllowed(req, env))) {
    return jsonResponse(429, {
      ok: false,
      error: "Too many run uploads. Please try again in a moment.",
    });
  }

  const contentLength = Number(req.headers.get("Content-Length") ?? "0");
  if (Number.isFinite(contentLength) && contentLength > MAX_RUN_BODY_BYTES) {
    return badRequest("Request body too large.");
  }

  const rawText = await req.text();
  if (rawText.length > MAX_RUN_BODY_BYTES) {
    return badRequest("Request body too large.");
  }

  let body: JsonObject;
  try {
    const parsed = JSON.parse(rawText) as unknown;
    if (!isJsonObject(parsed)) {
      return badRequest("Body must be a JSON object.");
    }
    body = parsed;
  } catch {
    return badRequest("Invalid JSON body.");
  }

  const playerEmail = normalizeEmail(body.player_email);
  if (!playerEmail) {
    return badRequest("Missing or invalid player_email.");
  }

  const playerName = trimString(body.player_name, MAX_PLAYER_FIELD_CHARS) || playerEmail;
  const playerUsername = trimString(body.player_username, MAX_PLAYER_FIELD_CHARS) || playerEmail;
  const run: JsonObject = isJsonObject(body.run) ? body.run : {};
  const quiz: JsonObject = isJsonObject(body.quiz) ? body.quiz : {};
  const hitObjectIds = toStringList(run.hit_object_ids, MAX_HIT_IDS);
  const answers = normalizeQuizAnswers(quiz.answers);

  const playerId = await upsertPlayerAndGetId(env, playerName, playerUsername, playerEmail);
  const result = await env.DB.prepare(
    `
      INSERT INTO run_sessions (
        player_id,
        started_at,
        ended_at,
        score,
        objects_hit_total,
        hit_object_ids,
        quiz_total_questions,
        quiz_correct_count,
        quiz_incorrect_count,
        quiz_answers_detail,
        player_size_px2,
        obstacle_size_px2,
        speed_start_pxps,
        speed_avg_pxps,
        speed_max_pxps,
        speed_end_pxps
      )
      VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12, ?13, ?14, ?15, ?16)
    `
  )
    .bind(
      playerId,
      toIsoStringOrNow(run.started_at),
      toIsoStringOrNow(run.ended_at),
      toNonNegativeInteger(run.score, 0),
      toNonNegativeInteger(run.objects_hit_total, hitObjectIds.length),
      hitObjectIds.join("|"),
      toNonNegativeInteger(quiz.quiz_total_questions, 0),
      toNonNegativeInteger(quiz.quiz_correct_count, 0),
      toNonNegativeInteger(quiz.quiz_incorrect_count, 0),
      JSON.stringify(answers),
      toNumber(run.player_size_px2, 0),
      toNumber(run.obstacle_size_px2, 0),
      toNumber(run.speed_start_pxps, 0),
      toNumber(run.speed_avg_pxps, 0),
      toNumber(run.speed_max_pxps, 0),
      toNumber(run.speed_end_pxps, 0)
    )
    .run();

  const sessionId = Number(result.meta.last_row_id ?? 0);
  return jsonResponse(201, { ok: true, session_id: sessionId, player_id: playerId });
}

async function handleListPlayers(req: Request, env: Env): Promise<Response> {
  if (!isAdminAuthorized(req, env)) {
    return unauthorized();
  }

  const rows = await env.DB.prepare(
    `
      SELECT
        p.id,
        p.display_name,
        p.username,
        p.email,
        COUNT(rs.id) AS run_count,
        MAX(rs.ended_at) AS last_run_at
      FROM players p
      LEFT JOIN run_sessions rs ON rs.player_id = p.id
      GROUP BY p.id, p.display_name, p.username, p.email
      ORDER BY LOWER(p.email) ASC
    `
  ).all<{
    id: number;
    display_name: string;
    username: string;
    email: string;
    run_count: number | string;
    last_run_at: string | null;
  }>();

  const players = (rows.results ?? []).map((row) => ({
    id: row.id,
    display_name: row.display_name,
    username: row.username,
    email: row.email,
    run_count: Number(row.run_count ?? 0),
    last_run_at: row.last_run_at,
  }));

  return jsonResponse(200, { ok: true, players });
}

async function handleListPlayerRuns(req: Request, env: Env, playerId: number): Promise<Response> {
  if (!isAdminAuthorized(req, env)) {
    return unauthorized();
  }

  const rows = await env.DB.prepare(
    `
      SELECT
        id,
        player_id,
        started_at,
        ended_at,
        score,
        objects_hit_total,
        hit_object_ids,
        quiz_total_questions,
        quiz_correct_count,
        quiz_incorrect_count,
        quiz_answers_detail,
        player_size_px2,
        obstacle_size_px2,
        speed_start_pxps,
        speed_avg_pxps,
        speed_max_pxps,
        speed_end_pxps
      FROM run_sessions
      WHERE player_id = ?1
      ORDER BY ended_at DESC, id DESC
    `
  )
    .bind(playerId)
    .all();

  return jsonResponse(200, { ok: true, runs: rows.results ?? [] });
}

async function handleExportCsv(req: Request, env: Env, playerId: number): Promise<Response> {
  if (!isAdminAuthorized(req, env)) {
    return unauthorized();
  }

  const player = await env.DB.prepare(
    `
      SELECT id, display_name, username, email
      FROM players
      WHERE id = ?1
    `
  )
    .bind(playerId)
    .first<{ id: number; display_name: string; username: string; email: string }>();

  if (!player) {
    return jsonResponse(404, { ok: false, error: "Player not found." });
  }

  const runs = await env.DB.prepare(
    `
      SELECT
        id,
        started_at,
        ended_at,
        score,
        objects_hit_total,
        hit_object_ids,
        quiz_total_questions,
        quiz_correct_count,
        quiz_incorrect_count,
        quiz_answers_detail,
        player_size_px2,
        obstacle_size_px2,
        speed_start_pxps,
        speed_avg_pxps,
        speed_max_pxps,
        speed_end_pxps
      FROM run_sessions
      WHERE player_id = ?1
      ORDER BY ended_at DESC, id DESC
    `
  )
    .bind(playerId)
    .all<{
      id: number;
      started_at: string;
      ended_at: string;
      score: number;
      objects_hit_total: number;
      hit_object_ids: string;
      quiz_total_questions: number;
      quiz_correct_count: number;
      quiz_incorrect_count: number;
      quiz_answers_detail: string;
      player_size_px2: number;
      obstacle_size_px2: number;
      speed_start_pxps: number;
      speed_avg_pxps: number;
      speed_max_pxps: number;
      speed_end_pxps: number;
    }>();

  const runsList = runs.results ?? [];
  const quizAnswersByRun = runsList.map((run) => parseQuizAnswers(run.quiz_answers_detail));
  const maxQuizAnswers = Math.max(0, ...quizAnswersByRun.map((answers) => answers.length));
  const exportedQuizAnswerColumns = Math.min(maxQuizAnswers, MAX_EXPORTED_QUIZ_QUESTION_COLUMNS);
  const hasExtraQuizAnswers = maxQuizAnswers > exportedQuizAnswerColumns;
  const quizAnswerHeaders: string[] = [];
  for (let index = 1; index <= exportedQuizAnswerColumns; index++) {
    quizAnswerHeaders.push(
      `Q${index} Question`,
      `Q${index} Player Answer`,
      `Q${index} Correct Answer`,
      `Q${index} Result`
    );
  }
  if (hasExtraQuizAnswers) {
    quizAnswerHeaders.push("Additional Quiz Answers Count");
  }

  const header: unknown[] = [
    "Player Name",
    "Username",
    "Email",
    "Run ID",
    "Run Started",
    "Run Ended",
    "Score",
    "Obstacles Hit",
    "Hit Obstacle IDs",
    "Quiz Total Questions",
    "Quiz Correct Answers",
    "Quiz Incorrect Answers",
    "Quiz Answers Summary",
    ...quizAnswerHeaders,
    "Player Size (px sq)",
    "Obstacle Size (px sq)",
    "Speed at Start (px/s)",
    "Average Speed (px/s)",
    "Peak Speed (px/s)",
    "Speed at End (px/s)",
  ];

  const csvRows: unknown[][] = [header];
  for (let index = 0; index < runsList.length; index++) {
    const run = runsList[index];
    const answers = quizAnswersByRun[index] ?? [];
    csvRows.push([
      player.display_name,
      player.username,
      player.email,
      run.id,
      run.started_at,
      run.ended_at,
      run.score,
      run.objects_hit_total,
      run.hit_object_ids,
      run.quiz_total_questions,
      run.quiz_correct_count,
      run.quiz_incorrect_count,
      formatQuizAnswerSummary(answers),
      ...quizAnswerCells(answers, exportedQuizAnswerColumns),
      ...(hasExtraQuizAnswers ? [Math.max(0, answers.length - exportedQuizAnswerColumns)] : []),
      run.player_size_px2,
      run.obstacle_size_px2,
      run.speed_start_pxps,
      run.speed_avg_pxps,
      run.speed_max_pxps,
      run.speed_end_pxps,
    ]);
  }

  const requester = (req.headers.get("X-Dev-User") ?? "unknown").slice(0, 128);
  await env.DB.prepare(
    `
      INSERT INTO dev_export_audit (player_id, requester)
      VALUES (?1, ?2)
    `
  )
    .bind(playerId, requester)
    .run();

  const stamp = new Date().toISOString().replace(/[-:]/g, "").replace(/\.\d+Z$/, "Z");
  const filename = `player_${playerId}_runs_${stamp}.csv`;
  return csvResponse(filename, toCsv(csvRows));
}

export default {
  async fetch(req: Request, env: Env): Promise<Response> {
    const url = new URL(req.url);
    const pathname = url.pathname;

    try {
      if (req.method === "GET" && pathname === "/health") {
        return jsonResponse(200, { ok: true, service: "arete-telemetry-api" });
      }

      if (req.method === "POST" && pathname === "/api/v1/runs") {
        return await handleCreateRun(req, env);
      }

      if (req.method === "GET" && pathname === "/api/v1/dev/players") {
        return await handleListPlayers(req, env);
      }

      if (req.method === "GET") {
        const runsPlayerId = parseIdSegment(pathname, "runs");
        if (runsPlayerId !== null) {
          return await handleListPlayerRuns(req, env, runsPlayerId);
        }

        const exportPlayerId = parseIdSegment(pathname, "export.csv");
        if (exportPlayerId !== null) {
          return await handleExportCsv(req, env, exportPlayerId);
        }
      }

      return jsonResponse(404, { ok: false, error: "Not found." });
    } catch (err) {
      console.error("arete-telemetry-api error", err);
      return serverError();
    }
  },
};
