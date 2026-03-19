'use client';

/**
 * VersionSelector — shadcn Select for switching document versions.
 * Shows version label, date, and trigger type.
 */
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { formatTimestamp } from '@/lib/document-formatters';

export interface DocVersion {
  version: string;
  created_at?: string;
  trigger?: string;
}

interface VersionSelectorProps {
  versions: DocVersion[];
  selectedVersion: string;
  onSelectVersion: (version: string) => void;
}

export function VersionSelector({ versions, selectedVersion, onSelectVersion }: VersionSelectorProps) {
  if (!versions.length) return null;

  return (
    <div className="space-y-1">
      <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
        Version
      </p>
      <Select value={selectedVersion} onValueChange={onSelectVersion}>
        <SelectTrigger className="h-8 text-xs bg-surface-2 border-border text-foreground">
          <SelectValue placeholder="Select version" />
        </SelectTrigger>
        <SelectContent className="bg-surface-1 border-border">
          {versions.map((v) => (
            <SelectItem key={v.version} value={v.version} className="text-xs">
              <span className="font-mono font-medium">{v.version}</span>
              {v.created_at && (
                <span className="ml-2 text-muted-foreground">
                  {formatTimestamp(v.created_at)}
                </span>
              )}
              {v.trigger && (
                <span className="ml-1 text-muted-foreground capitalize">
                  · {v.trigger.replace(/_/g, ' ')}
                </span>
              )}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
