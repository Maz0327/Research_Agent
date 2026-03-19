'use client';

/**
 * ThreeColumnLayout — responsive 3-panel grid for job detail pages.
 * Desktop (≥1280px): 280px left | flex-1 center | 320px right
 * Tablet (768–1279px): 280px left | flex-1 center | right panel hidden (Sheet trigger)
 * Mobile (<768px): single column; left panel as Collapsible, right as bottom Sheet
 */

import { useState } from 'react';
import { PanelLeftOpen, PanelRightOpen, X } from 'lucide-react';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Button } from '@/components/ui/button';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from '@/components/ui/sheet';
import { cn } from '@/lib/utils';

interface ThreeColumnLayoutProps {
  /** Left panel content (job meta, source nav) — 280px on desktop */
  leftPanel: React.ReactNode;
  /** Center main content (documents, accordion) — flex-1 */
  centerContent: React.ReactNode;
  /** Right panel content (activity log, chat) — 320px on desktop */
  rightPanel: React.ReactNode;
  /** Optional full-width status bar rendered above the columns */
  statusBar?: React.ReactNode;
  /** Label for right panel Sheet trigger on tablet */
  rightPanelLabel?: string;
  /** Label for left panel Collapsible toggle on mobile */
  leftPanelLabel?: string;
}

export function ThreeColumnLayout({
  leftPanel,
  centerContent,
  rightPanel,
  statusBar,
  rightPanelLabel = 'Activity',
  leftPanelLabel = 'Job Details',
}: ThreeColumnLayoutProps) {
  const [leftOpen, setLeftOpen] = useState(false);
  const [rightSheetOpen, setRightSheetOpen] = useState(false);

  return (
    <div className="flex flex-col h-full">
      {/* Optional full-width status bar */}
      {statusBar && (
        <div className="flex-shrink-0 border-b border-border">
          {statusBar}
        </div>
      )}

      {/* === Desktop (≥1280px): 3-column CSS grid === */}
      <div className="hidden xl:grid xl:grid-cols-[280px_1fr_320px] flex-1 min-h-0 overflow-hidden">
        {/* Left */}
        <aside className="border-r border-border overflow-hidden">
          <ScrollArea className="h-full">
            <div className="p-4">{leftPanel}</div>
          </ScrollArea>
        </aside>

        {/* Center */}
        <main className="overflow-hidden">
          <ScrollArea className="h-full">
            <div className="p-4">{centerContent}</div>
          </ScrollArea>
        </main>

        {/* Right */}
        <aside className="border-l border-border overflow-hidden">
          <ScrollArea className="h-full">
            <div className="p-4">{rightPanel}</div>
          </ScrollArea>
        </aside>
      </div>

      {/* === Tablet (768–1279px): 2-column, right panel via Sheet === */}
      <div className="hidden md:flex xl:hidden flex-1 min-h-0 overflow-hidden">
        {/* Left */}
        <aside className="w-[280px] border-r border-border overflow-hidden flex-shrink-0">
          <ScrollArea className="h-full">
            <div className="p-4">{leftPanel}</div>
          </ScrollArea>
        </aside>

        {/* Center + right Sheet trigger */}
        <div className="flex flex-1 flex-col min-w-0 overflow-hidden">
          {/* Tablet toolbar */}
          <div className="flex items-center justify-end px-4 py-2 border-b border-border flex-shrink-0">
            <Sheet open={rightSheetOpen} onOpenChange={setRightSheetOpen}>
              <SheetTrigger asChild>
                <Button variant="ghost" size="sm" className="gap-2 text-muted-foreground">
                  <PanelRightOpen className="h-4 w-4" aria-hidden="true" />
                  {rightPanelLabel}
                </Button>
              </SheetTrigger>
              <SheetContent side="right" className="w-80 p-0 bg-surface-1 border-border">
                <SheetHeader className="px-4 py-3 border-b border-border">
                  <SheetTitle className="text-sm">{rightPanelLabel}</SheetTitle>
                </SheetHeader>
                <ScrollArea className="h-full">
                  <div className="p-4">{rightPanel}</div>
                </ScrollArea>
              </SheetContent>
            </Sheet>
          </div>

          <main className="flex-1 overflow-hidden">
            <ScrollArea className="h-full">
              <div className="p-4">{centerContent}</div>
            </ScrollArea>
          </main>
        </div>
      </div>

      {/* === Mobile (<768px): single column === */}
      <div className="flex md:hidden flex-col flex-1 min-h-0 overflow-hidden">
        {/* Left panel as Collapsible */}
        <Collapsible open={leftOpen} onOpenChange={setLeftOpen}>
          <CollapsibleTrigger asChild>
            <Button
              variant="ghost"
              size="sm"
              className={cn(
                'w-full justify-between rounded-none border-b border-border px-4 py-3 text-sm font-medium',
                leftOpen && 'bg-surface-1'
              )}
            >
              <span className="flex items-center gap-2">
                <PanelLeftOpen className="h-4 w-4" aria-hidden="true" />
                {leftPanelLabel}
              </span>
              <X
                className={cn(
                  'h-4 w-4 transition-transform text-muted-foreground',
                  !leftOpen && 'rotate-45'
                )}
                aria-hidden="true"
              />
            </Button>
          </CollapsibleTrigger>
          <CollapsibleContent>
            <div className="border-b border-border bg-surface-1 p-4">
              {leftPanel}
            </div>
          </CollapsibleContent>
        </Collapsible>

        {/* Center content — main scrollable area */}
        <main className="flex-1 overflow-y-auto">
          <div className="p-4">{centerContent}</div>
        </main>

        {/* Right panel — bottom Sheet */}
        <Sheet open={rightSheetOpen} onOpenChange={setRightSheetOpen}>
          <SheetTrigger asChild>
            <Button
              size="sm"
              variant="outline"
              className="fixed bottom-4 right-4 z-20 gap-2 shadow-lg"
            >
              <PanelRightOpen className="h-4 w-4" aria-hidden="true" />
              {rightPanelLabel}
            </Button>
          </SheetTrigger>
          <SheetContent side="bottom" className="h-[60vh] p-0 bg-surface-1 border-border">
            <SheetHeader className="px-4 py-3 border-b border-border">
              <SheetTitle className="text-sm">{rightPanelLabel}</SheetTitle>
            </SheetHeader>
            <ScrollArea className="h-full">
              <div className="p-4">{rightPanel}</div>
            </ScrollArea>
          </SheetContent>
        </Sheet>
      </div>
    </div>
  );
}
