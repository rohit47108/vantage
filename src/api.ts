export async function readResponse(response: Response) {
  if (!response.ok) {
    let detail = `Service unavailable (${response.status}). Retry or choose a prepared example.`;
    if (response.headers.get("content-type")?.includes("application/json")) {
      const body = await response.json();
      if (typeof body.detail === "string") detail = body.detail;
      else if (Array.isArray(body.detail))
        detail = body.detail
          .map((item: { msg: string }) => item.msg)
          .join(". ");
    }
    throw new Error(detail);
  }
  return response.json();
}

export async function json<T = any>(url: string, options?: RequestInit): Promise<T> {
  return readResponse(await fetch(url, options));
}
