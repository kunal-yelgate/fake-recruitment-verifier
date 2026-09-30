# Scanner inputs

## Pasted text and text files

Paste the recruiter message or job posting into the scanner, or upload a
`.txt`, `.md`, or `.eml` file. The browser limits imported text to 10,000
characters, matching the API request limit. Review and edit imported content
before selecting **Run OSINT Verification**.

## Public URL import

Signed-in users can enter an `http://` or `https://` job-posting URL and select
**Fetch posting**. The frontend sends the URL to the authenticated
`POST /fetch-url` endpoint. The backend revalidates every redirect, resolves
DNS, rejects private/loopback/link-local addresses, limits redirects and
response bytes, and accepts only bounded text or HTML responses. It does not
send cookies or user credentials to the target site. The returned text is
placed in the editable scanner field; it is never scanned automatically.

URL import is intended for public pages. If a site requires a login, blocks
automated requests, renders its content only in a browser, or returns a PDF or
image, paste the relevant text instead.

## OCR status

Screenshot OCR remains deferred. There is currently no vetted OCR dependency,
isolated image-processing worker, upload-size/content validation boundary, or
retention policy in this application. Enabling OCR in the existing API would
expand the attack surface and could allow untrusted image processing to run
inside the authenticated web process. OCR can be reconsidered as a separately
feature-flagged service after those controls and a maintained dependency are
available.
