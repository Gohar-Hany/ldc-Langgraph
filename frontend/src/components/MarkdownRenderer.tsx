import React from 'react';
import { Copy, Check } from 'lucide-react';

interface MarkdownRendererProps {
  content: string;
}

export const MarkdownRenderer: React.FC<MarkdownRendererProps> = ({ content }) => {
  const [copiedIndex, setCopiedIndex] = React.useState<number | null>(null);

  const handleCopy = (text: string, index: number) => {
    navigator.clipboard.writeText(text);
    setCopiedIndex(index);
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  // Process text into segments (code blocks vs text/tables/lists)
  const renderFormattedText = (raw: string) => {
    // Basic regex-based rich parser that creates native React elements
    const lines = raw.split('\n');
    const elements: React.ReactNode[] = [];
    let inList = false;
    let listItems: React.ReactNode[] = [];
    let inTable = false;
    let tableRows: string[][] = [];

    const flushList = () => {
      if (inList && listItems.length > 0) {
        elements.push(
          <ul key={`list-${elements.length}`} style={{ paddingLeft: '20px', margin: '8px 0', color: 'var(--text-secondary)' }}>
            {listItems}
          </ul>
        );
        listItems = [];
        inList = false;
      }
    };

    const flushTable = () => {
      if (inTable && tableRows.length > 0) {
        const header = tableRows[0];
        const body = tableRows.slice(2); // Skip separator row
        elements.push(
          <div key={`table-${elements.length}`} style={{ overflowX: 'auto', margin: '12px 0' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px', background: '#fff', border: '1px solid var(--border-light)', borderRadius: '6px' }}>
              <thead>
                <tr style={{ background: '#f8fafc', borderBottom: '2px solid var(--border-light)' }}>
                  {header.map((col, ci) => (
                    <th key={ci} style={{ padding: '8px 12px', textAlign: 'left', fontWeight: 600, color: 'var(--text-primary)' }}>
                      {formatInline(col.trim())}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {body.map((row, ri) => (
                  <tr key={ri} style={{ borderBottom: '1px solid var(--border-light)' }}>
                    {row.map((cell, ci) => (
                      <td key={ci} style={{ padding: '8px 12px', color: 'var(--text-secondary)' }}>
                        {formatInline(cell.trim())}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        );
        tableRows = [];
        inTable = false;
      }
    };

    const formatInline = (text: string): React.ReactNode => {
      // Bold **text**
      const parts = text.split(/(\*\*.*?\*\*|`.*?`)/g);
      return parts.map((part, i) => {
        if (part.startsWith('**') && part.endsWith('**')) {
          return <strong key={i} style={{ color: 'var(--text-primary)', fontWeight: 700 }}>{part.slice(2, -2)}</strong>;
        }
        if (part.startsWith('`') && part.endsWith('`')) {
          return (
            <code
              key={i}
              style={{
                background: '#f1f5f9',
                color: 'var(--ldc-green-dark)',
                padding: '2px 5px',
                borderRadius: '4px',
                fontSize: '12px',
                fontFamily: 'var(--font-mono)',
                fontWeight: 600,
                border: '1px solid #e2e8f0',
              }}
            >
              {part.slice(1, -1)}
            </code>
          );
        }
        return part;
      });
    };

    lines.forEach((line, idx) => {
      const trimmed = line.trim();

      // Table row detection
      if (trimmed.startsWith('|') && trimmed.endsWith('|')) {
        flushList();
        inTable = true;
        const cols = trimmed.slice(1, -1).split('|');
        tableRows.push(cols);
        return;
      } else {
        flushTable();
      }

      // Heading 3
      if (trimmed.startsWith('### ')) {
        flushList();
        elements.push(
          <h3 key={idx} style={{ fontSize: '15px', fontWeight: 700, margin: '14px 0 6px', color: 'var(--text-primary)' }}>
            {formatInline(trimmed.slice(4))}
          </h3>
        );
        return;
      }

      // Heading 2
      if (trimmed.startsWith('## ')) {
        flushList();
        elements.push(
          <h2 key={idx} style={{ fontSize: '17px', fontWeight: 700, margin: '16px 0 8px', color: 'var(--text-primary)', borderBottom: '1px solid var(--border-light)', paddingBottom: '4px' }}>
            {formatInline(trimmed.slice(3))}
          </h2>
        );
        return;
      }

      // Heading 1
      if (trimmed.startsWith('# ')) {
        flushList();
        elements.push(
          <h1 key={idx} style={{ fontSize: '19px', fontWeight: 800, margin: '18px 0 8px', color: 'var(--text-primary)' }}>
            {formatInline(trimmed.slice(2))}
          </h1>
        );
        return;
      }

      // List Item
      if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
        inList = true;
        listItems.push(
          <li key={idx} style={{ margin: '3px 0', lineHeight: 1.5 }}>
            {formatInline(trimmed.slice(2))}
          </li>
        );
        return;
      }

      // Numbered List Item
      const numMatch = trimmed.match(/^(\d+)\.\s+(.*)/);
      if (numMatch) {
        inList = true;
        listItems.push(
          <li key={idx} style={{ margin: '3px 0', lineHeight: 1.5 }}>
            {formatInline(numMatch[2])}
          </li>
        );
        return;
      }

      // Regular Paragraph or empty line
      flushList();
      if (trimmed) {
        elements.push(
          <p key={idx} style={{ margin: '6px 0', lineHeight: 1.6, color: 'var(--text-secondary)' }}>
            {formatInline(line)}
          </p>
        );
      }
    });

    flushList();
    flushTable();

    return elements;
  };

  // Split code blocks from prose
  const parts = content.split(/(```[\s\S]*?```)/g);

  return (
    <div style={{ fontSize: '14px', lineHeight: 1.6 }}>
      {parts.map((part, index) => {
        if (part.startsWith('```') && part.endsWith('```')) {
          const codeContent = part.slice(3, -3);
          const firstNewline = codeContent.indexOf('\n');
          const language = firstNewline !== -1 ? codeContent.slice(0, firstNewline).trim() : '';
          const code = firstNewline !== -1 ? codeContent.slice(firstNewline + 1) : codeContent;

          return (
            <div
              key={index}
              style={{
                margin: '12px 0',
                borderRadius: '8px',
                background: '#0f172a',
                border: '1px solid #334155',
                overflow: 'hidden',
              }}
            >
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  padding: '6px 12px',
                  background: '#1e293b',
                  borderBottom: '1px solid #334155',
                  fontSize: '11px',
                  color: '#94a3b8',
                  fontFamily: 'var(--font-mono)',
                  fontWeight: 600,
                  textTransform: 'uppercase',
                }}
              >
                <span>{language || 'code'}</span>
                <button
                  onClick={() => handleCopy(code, index)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '4px',
                    color: copiedIndex === index ? '#4ade80' : '#94a3b8',
                    background: 'transparent',
                    padding: '2px 6px',
                    borderRadius: '4px',
                    fontSize: '11px',
                  }}
                  title="Copy code"
                >
                  {copiedIndex === index ? <Check size={12} /> : <Copy size={12} />}
                  <span>{copiedIndex === index ? 'Copied' : 'Copy'}</span>
                </button>
              </div>
              <pre
                style={{
                  margin: 0,
                  padding: '12px',
                  fontFamily: 'var(--font-mono)',
                  fontSize: '12.5px',
                  color: '#e2e8f0',
                  overflowX: 'auto',
                  lineHeight: 1.5,
                }}
              >
                <code>{code}</code>
              </pre>
            </div>
          );
        }
        return <div key={index}>{renderFormattedText(part)}</div>;
      })}
    </div>
  );
};
