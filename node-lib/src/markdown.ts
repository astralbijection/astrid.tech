import fs from "fs";
import { join } from "path";
import rehypeHighlight from "rehype-highlight";
import remark from "remark";
import { VFile } from "vfile";

import { truncateKeepWords } from "./util";

const graphviz = require("remark-graphviz");
const math = require("remark-math");
const unwrapImages = require("remark-unwrap-images");
const picture = require("rehype-picture");
const remark2rehype = require("remark-rehype");
const html = require("rehype-stringify");
const katex = require("rehype-katex");
const footnotes = require("remark-footnotes");
const raw = require("rehype-raw");
const oembed = require("remark-oembed");
const markdown = require("remark-parse");
const unified = require("unified");
const slug = require("remark-slug");
const gfm = require("remark-gfm");
const urls = require("rehype-urls");
const excerpt = require("remark-excerpt");
const toPlainText = require("remark-plain-text");
const emoji = require("remark-emoji");

const publicRoot = join(process.cwd(), "public");

export async function renderMarkdown(md: string, assetRoot: string) {
  function convertRelativeFileRef(url: URL) {
    if (
      url.hostname == null &&
      url.pathname != null &&
      url.pathname[0] != "/"
    ) {
      const newPath = join("/_", assetRoot, url.pathname);
      const expectedFile = join(publicRoot, newPath);
      if (fs.existsSync(expectedFile) && fs.statSync(expectedFile).isFile()) {
        return newPath;
      }
    }
    return url;
  }

  const vfile = new VFile(md);
  vfile.data = { destinationDir: join("./public/_", assetRoot) };

  const out = await unified()
    .use(markdown)
    .use(graphviz)
    .use(slug)
    .use(oembed)
    .use(emoji)
    .use(gfm)
    .use(unwrapImages)
    .use(math)
    .use(footnotes)
    .use(remark2rehype, { allowDangerousHtml: true })
    .use(raw)
    .use(rehypeHighlight)
    .use(urls, convertRelativeFileRef)
    .use(katex)
    .use(picture)
    .use(html, { sanitize: false })
    .process(vfile);

  return out.toString() as string;
}

export async function getMarkdownExcerpt(md: string, maxChars: number) {
  const text = (
    await remark().use(excerpt).use(toPlainText).process(md)
  ).toString() as string;
  const result = truncateKeepWords(text, maxChars);
  if (result.neededTruncation) {
    return result.truncated + "\u2026"; // ellipsis
  }
  return result.truncated;
}

export function withoutContent<T>(object: { content: string } & T) {
  const out = {
    ...object,
  } as { content?: string } & T;
  delete out.content;
  return out as { content: never } & T;
}

export const excerptify =
  (maxChars: number) =>
  async <T>(
    object: { content: string } & T
  ): Promise<{ excerpt?: string } & T> =>
    withoutContent({
      ...object,
      excerpt: await getMarkdownExcerpt(object.content, maxChars),
    });
