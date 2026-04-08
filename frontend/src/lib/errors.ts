import { AxiosError } from "axios";

/**
 * Extract a user-facing error message from an axios/FastAPI error.
 *
 * FastAPI returns `detail` in two shapes:
 *   - HTTPException: detail is a string
 *   - RequestValidationError (422): detail is an array of
 *     {loc, msg, type, ...} objects
 *
 * We normalize both (and any unexpected shape) into a plain string so
 * rendering it as a React child never throws.
 */
export function extractErrorMessage(err: unknown, fallback = "Something went wrong"): string {
  if (!err) return fallback;
  if (err instanceof AxiosError) {
    const detail = err.response?.data?.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      return detail
        .map((d: any) => {
          const loc = Array.isArray(d?.loc) ? d.loc.slice(1).join(".") : "";
          const msg = typeof d?.msg === "string" ? d.msg : "invalid";
          return loc ? `${loc}: ${msg}` : msg;
        })
        .join("; ");
    }
    if (err.message) return err.message;
  }
  if (err instanceof Error) return err.message;
  return fallback;
}
