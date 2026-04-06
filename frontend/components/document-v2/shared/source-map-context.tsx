'use client';

/**
 * source-map-context — React context that distributes source_id → SourceInfo map
 * to all document renderers. Avoids prop-drilling through every renderer/sub-component.
 */

import { createContext, useContext } from 'react';
import type { SourceMap } from '@/lib/source-map-utils';

const SourceMapContext = createContext<SourceMap>({});

export function SourceMapProvider({
  sourceMap,
  children,
}: {
  sourceMap: SourceMap;
  children: React.ReactNode;
}) {
  return (
    <SourceMapContext.Provider value={sourceMap}>
      {children}
    </SourceMapContext.Provider>
  );
}

/** Returns the source map. Empty object when no provider present (graceful degradation). */
export function useSourceMap(): SourceMap {
  return useContext(SourceMapContext);
}
