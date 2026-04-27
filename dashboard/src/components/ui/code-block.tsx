'use client';

import * as React from 'react';
import { cn } from '@/lib/utils';

type Lang = 'json' | 'python' | 'text';

interface CodeBlockProps {
  code: string;
  language?: Lang;
  className?: string;
}

const KEYWORDS = new Set([
  'def', 'class', 'return', 'if', 'else', 'elif', 'for', 'while', 'in',
  'import', 'from', 'as', 'with', 'try', 'except', 'finally', 'raise',
  'yield', 'await', 'async', 'pass', 'break', 'continue', 'lambda',
  'True', 'False', 'None', 'and', 'or', 'not', 'is'
]);

function highlightPython(src: string): React.ReactNode {
  const tokens: React.ReactNode[] = [];
  const re = /("(?:[^"\\]|\\.)*")|('(?:[^'\\]|\\.)*')|(#[^\n]*)|(\b\d+(?:\.\d+)?\b)|(\b[A-Za-z_][A-Za-z0-9_]*\b)|(\s+)|([^\s])/g;
  let m;
  let i = 0;
  while ((m = re.exec(src)) !== null) {
    const [, str1, str2, com, num, ident, ws, sym] = m;
    const key = i++;
    if (str1 || str2) tokens.push(<span key={key} className="tk-s">{str1 ?? str2}</span>);
    else if (com) tokens.push(<span key={key} className="tk-c">{com}</span>);
    else if (num) tokens.push(<span key={key} className="tk-n">{num}</span>);
    else if (ident) {
      if (KEYWORDS.has(ident)) tokens.push(<span key={key} className="tk-k">{ident}</span>);
      else if (/^[a-z_][A-Za-z0-9_]*$/.test(ident) && src[m.index + ident.length] === '(') tokens.push(<span key={key} className="tk-f">{ident}</span>);
      else tokens.push(ident);
    } else if (ws) tokens.push(ws);
    else if (sym) {
      if (':,;[]{}'.includes(sym)) tokens.push(<span key={key} className="tk-p">{sym}</span>);
      else tokens.push(sym);
    }
  }
  return tokens;
}

function highlightJson(src: string): React.ReactNode {
  const tokens: React.ReactNode[] = [];
  const re = /("(?:[^"\\]|\\.)*"\s*:)|("(?:[^"\\]|\\.)*")|(\b(?:true|false|null)\b)|(-?\d+(?:\.\d+)?)|(\s+)|([^\s])/g;
  let m;
  let i = 0;
  while ((m = re.exec(src)) !== null) {
    const [, key, str, kw, num, ws, sym] = m;
    const k = i++;
    if (key) tokens.push(<span key={k} className="tk-f">{key}</span>);
    else if (str) tokens.push(<span key={k} className="tk-s">{str}</span>);
    else if (kw) tokens.push(<span key={k} className="tk-k">{kw}</span>);
    else if (num) tokens.push(<span key={k} className="tk-n">{num}</span>);
    else if (ws) tokens.push(ws);
    else if (sym) {
      if ('{}[],:'.includes(sym)) tokens.push(<span key={k} className="tk-p">{sym}</span>);
      else tokens.push(sym);
    }
  }
  return tokens;
}

export function CodeBlock({ code, language = 'text', className }: CodeBlockProps) {
  let content: React.ReactNode = code;
  if (language === 'python') content = highlightPython(code);
  else if (language === 'json') content = highlightJson(code);
  return <pre className={cn('snip', className)}>{content}</pre>;
}
