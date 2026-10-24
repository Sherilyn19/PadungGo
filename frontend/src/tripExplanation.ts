import { ApiError, type ExplainResponse } from './api'

// What the "Explain this trip" panel shows. The explanation never blocks the
// itinerary: every failure ends in 'unavailable', never in an exception.
export type ExplanationState =
  | { phase: 'idle' }
  | { phase: 'loading' }
  | { phase: 'ready'; paragraphs: string[]; notices: string[]; model: string }
  | { phase: 'unavailable'; message: string; retryable: boolean }

export const IDLE: ExplanationState = { phase: 'idle' }
export const LOADING: ExplanationState = { phase: 'loading' }

const UNAVAILABLE_MESSAGE = 'The explanation is unavailable right now.'

function isStringArray(value: unknown): value is string[] {
  return Array.isArray(value) && value.every((item) => typeof item === 'string')
}

// Checks the server's answer before anything is shown. Text that is not
// labelled as AI-generated is refused, so an unlabelled explanation can never
// reach the screen.
export function parseExplainResponse(body: unknown): ExplainResponse | null {
  if (typeof body !== 'object' || body === null) return null
  const data = body as Record<string, unknown>
  if (data.status === 'ok') {
    if (typeof data.explanation !== 'string' || data.explanation.trim() === '') return null
    if (data.ai_generated !== true || !isStringArray(data.notices)) return null
    return {
      status: 'ok',
      explanation: data.explanation,
      notices: data.notices,
      ai_generated: true,
      model: typeof data.model === 'string' ? data.model : '',
    }
  }
  if (data.status === 'unavailable') {
    if (typeof data.message !== 'string' || typeof data.retryable !== 'boolean') return null
    return {
      status: 'unavailable',
      reason: typeof data.reason === 'string' ? data.reason : 'error',
      message: data.message,
      retryable: data.retryable,
    }
  }
  return null
}

export function explanationFromResponse(body: unknown): ExplanationState {
  const parsed = parseExplainResponse(body)
  if (parsed === null) return { phase: 'unavailable', message: UNAVAILABLE_MESSAGE, retryable: true }
  if (parsed.status === 'unavailable') {
    return { phase: 'unavailable', message: parsed.message, retryable: parsed.retryable }
  }
  return {
    phase: 'ready',
    paragraphs: parsed.explanation.split('\n').map((line) => line.trim()).filter(Boolean),
    notices: parsed.notices,
    model: parsed.model,
  }
}

// HTTP-level failures (busy, trip changed, offline). The messages from
// ApiError are already plain language.
export function explanationFromError(error: unknown): ExplanationState {
  if (error instanceof ApiError) {
    return { phase: 'unavailable', message: error.message, retryable: error.retryable }
  }
  return { phase: 'unavailable', message: UNAVAILABLE_MESSAGE, retryable: true }
}

// --- Presentation helpers (pure, so they are easy to test) ---------------------

export interface AnimatedWord {
  text: string
  // Position across the whole summary, used to stagger the fade-in.
  index: number
}

// Splits the summary into words for the word-by-word reveal. The index runs
// across paragraphs, so the whole text appears as one smooth sentence.
export function animatedParagraphs(paragraphs: string[]): AnimatedWord[][] {
  let index = 0
  return paragraphs.map((paragraph) =>
    paragraph
      .split(/\s+/)
      .filter(Boolean)
      .map((text) => ({ text, index: index++ })),
  )
}

// The summary no longer repeats the data warning, so the card carries one short
// friendly reminder of its own, only when the server says the data is historic.
export function showsOlderRecordsReminder(notices: string[]): boolean {
  return notices.some((notice) => /not field-verified/i.test(notice))
}

// "openai/gpt-oss-20b" -> "gpt-oss-20b".
export function shortModelName(model: string): string {
  return model.split('/').pop()?.trim() ?? ''
}
