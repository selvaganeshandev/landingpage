import { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/hooks/use-toast";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { apiClient } from "@/services/api";
import { useDomainStore } from "@/stores/domainStore";
import {
  FileText,
  Plus,
  Loader2,
  Trash2,
  Pencil,
  Check,
  X,
  MoreVertical,
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
  Calendar,
  ArrowUpDown,
  Download,
} from "lucide-react";
import { getFaviconUrl, handleFaviconError } from "@/utils/faviconHelper";

const ROWS_PER_PAGE_OPTIONS = [5, 10, 25, 50];
const DEFAULT_ROWS_PER_PAGE = 5;

const SHEET_TYPE_LABELS: Record<string, string> = {
  gsc_queries: "GSC Queries",
  gsc_branded_queries: "Branded Queries",
  gsc_non_branded_queries: "Non-Branded Queries",
  gsc_pages: "Pages",
  ga_landing_pages: "Landing Pages",
  ga_other_sources: "Other Sources",
  ga_overview: "GA Overview",
  keyword_ranking: "Keyword Ranking",
  domain_metrics: "Domain Metrics",
  gsc_overview: "GSC Overview",
  keyword_ranking_overview: "Keyword Ranking Overview",
};

const SeoReports = () => {
  const navigate = useNavigate();
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const { selectedDomain } = useDomainStore();
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [sheetToDelete, setSheetToDelete] = useState<number | null>(null);
  const [exporting, setExporting] = useState(false);

  const domainId = selectedDomain?.id;

  useEffect(() => {
    if (domainId) {
      queryClient.invalidateQueries({ queryKey: ["seoReportSheets"] });
      queryClient.invalidateQueries({ queryKey: ["seoReportData"] });
    }
  }, [domainId, queryClient]);

  // Fetch sheet configs
  const { data: sheetsData, isLoading: sheetsLoading } = useQuery({
    queryKey: ["seoReportSheets", domainId],
    queryFn: async () => {
      const res = await apiClient.getSeoReportSheets(domainId!);
      return res as { sheets: any[]; count: number };
    },
    enabled: !!domainId,
  });

  const sheets = sheetsData?.sheets || [];

  // Fetch report data (live GSC/GA)
  const {
    data: reportData,
    isLoading: dataLoading,
    isError: dataError,
  } = useQuery({
    queryKey: ["seoReportData", domainId],
    queryFn: async () => {
      const res = await apiClient.getSeoReportSheetData(domainId!);
      return res as { reports: any[]; count: number };
    },
    enabled: !!domainId && sheets.length > 0,
    retry: 1,
  });

  const reports = reportData?.reports || [];

  // Map report data by sheet_id for quick lookup
  const reportBySheetId: Record<number, any> = {};
  reports.forEach((r) => {
    reportBySheetId[r.sheet_id] = r;
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: (id: number) => apiClient.deleteSeoReportSheet(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["seoReportSheets"] });
      queryClient.invalidateQueries({ queryKey: ["seoReportData"] });
      toast({ title: "Deleted", description: "Report sheet deleted successfully." });
    },
    onError: (err: any) => {
      toast({
        title: "Error",
        description: err.message || "Failed to delete.",
        variant: "destructive",
      });
    },
  });

  const handleDelete = (id: number) => {
    setSheetToDelete(id);
    setDeleteDialogOpen(true);
  };

  const confirmDelete = () => {
    if (sheetToDelete) {
      deleteMutation.mutate(sheetToDelete);
      setDeleteDialogOpen(false);
      setSheetToDelete(null);
    }
  };

  const handleExportXlsx = async () => {
    if (!domainId) return;
    setExporting(true);
    try {
      const blob = await apiClient.exportSeoReportXlsx(domainId);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      const now = new Date();
      const ts = now.getFullYear().toString()
        + String(now.getMonth() + 1).padStart(2, "0")
        + String(now.getDate()).padStart(2, "0")
        + "_" + String(now.getHours()).padStart(2, "0")
        + String(now.getMinutes()).padStart(2, "0")
        + String(now.getSeconds()).padStart(2, "0");
      link.setAttribute("download", `seo-report-${selectedDomain?.name || domainId}-${ts}.xlsx`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      toast({ title: "Report exported successfully" });
    } catch {
      toast({ title: "Export failed", variant: "destructive" });
    } finally {
      setExporting(false);
    }
  };

  if (!domainId) {
    return (
      <div className="p-8">
        <div>
          <h1 className="text-4xl font-bold tracking-tight">Organic Reports</h1>
          <p className="text-muted-foreground mt-2">SEO performance reports</p>
        </div>
        <Card className="p-12 mt-8 text-center">
          <FileText className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
          <p className="text-muted-foreground">
            Please select a domain to view reports.
          </p>
        </Card>
      </div>
    );
  }

  const isLoading = sheetsLoading;
  const showEmptyState = !isLoading && sheets.length === 0;

  return (
    <div className="p-8 space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0">
            <img
              src={getFaviconUrl(selectedDomain?.url || "", 64)}
              alt=""
              className="h-8 w-8 rounded"
              onError={(e) =>
                handleFaviconError(
                  e,
                  selectedDomain?.url || "",
                  selectedDomain?.name || "",
                  64
                )
              }
            />
          </div>
          <div>
            <h1 className="text-4xl font-bold tracking-tight">Reports</h1>
            {selectedDomain?.url && (
              <a
                href={selectedDomain.url}
                target="_blank"
                rel="noreferrer"
                className="text-sm text-muted-foreground hover:text-primary transition-colors"
              >
                {selectedDomain.url.replace(/^https?:\/\//, "")}
              </a>
            )}
          </div>
        </div>

        {sheets.length > 0 && (
          <div className="flex gap-2">
            <Button variant="outline" onClick={handleExportXlsx} disabled={exporting}>
              {exporting ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <Download className="h-4 w-4 mr-2" />
              )}
              {exporting ? "Exporting..." : "Export"}
            </Button>
            <Button onClick={() => navigate("/seo-reports/configure")}>
              <Plus className="h-4 w-4 mr-2" />
              Add Report
            </Button>
          </div>
        )}
      </div>

      {/* Loading */}
      {isLoading && (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      )}

      {/* Empty State */}
      {showEmptyState && (
        <Card className="p-12 text-center">
          <h2 className="text-2xl font-bold mb-2">Configure Report</h2>
          <p className="text-muted-foreground mb-6">
            Customize and control reports. If you've added the report, please
            check back in 5 minutes.
          </p>
          <Button
            size="lg"
            onClick={() => navigate("/seo-reports/configure")}
          >
            Let's start
          </Button>
        </Card>
      )}

      {/* Report Widgets */}
      {!isLoading && sheets.length > 0 && (
        <div className="space-y-8">
          {sheets.map((sheet) => (
            <ReportWidget
              key={sheet.id}
              sheet={sheet}
              reportData={reportBySheetId[sheet.id]}
              dataLoading={dataLoading}
              dataError={dataError}
              onDelete={handleDelete}
              onRename={(id, name) => {
                apiClient
                  .updateSeoReportSheet(id, { sheet_name: name })
                  .then(() => {
                    queryClient.invalidateQueries({
                      queryKey: ["seoReportSheets"],
                    });
                    queryClient.invalidateQueries({
                      queryKey: ["seoReportData"],
                    });
                    toast({ title: "Renamed", description: "Report renamed." });
                  });
              }}
            />
          ))}
        </div>
      )}

      {/* Delete Dialog */}
      <ConfirmDialog
        open={deleteDialogOpen}
        onOpenChange={setDeleteDialogOpen}
        title="Delete Report Sheet"
        description="Are you sure you want to delete this report sheet? This action cannot be undone."
        confirmText="Delete"
        onConfirm={confirmDelete}
        variant="destructive"
      />
    </div>
  );
};

// ─── Report Widget ───────────────────────────────────────────────────────────

function ReportWidget({
  sheet,
  reportData,
  dataLoading,
  dataError,
  onDelete,
  onRename,
}: {
  sheet: any;
  reportData: any | undefined;
  dataLoading: boolean;
  dataError: boolean;
  onDelete: (id: number) => void;
  onRename: (id: number, name: string) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [editName, setEditName] = useState(sheet.sheet_name);
  const [menuOpen, setMenuOpen] = useState(false);
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(DEFAULT_ROWS_PER_PAGE);
  const menuRef = useRef<HTMLDivElement>(null);

  const columns: string[] = reportData?.columns || [];
  const allRows: any[] = reportData?.rows || [];
  const totalRows = allRows.length;
  const hasSrNo = columns.includes("Sr No");
  const totalPages = Math.max(1, Math.ceil(totalRows / rowsPerPage));
  const paginatedRows = allRows.slice(
    page * rowsPerPage,
    (page + 1) * rowsPerPage
  );

  const hasData = columns.length > 0 && allRows.length > 0;
  const rawError = reportData?.error;
  // Show user-friendly error messages instead of raw API errors
  const errorMsg = rawError
    ? rawError.includes("not connected")
      ? rawError
      : rawError.includes("permission")
        ? "Insufficient permissions. Please reconnect Google Search Console with the correct account."
        : rawError.includes("credentials") || rawError.includes("token")
          ? "Your integration credentials have expired. Please reconnect in Domain Settings."
          : "Unable to fetch report data. Please check your integration settings."
    : null;
  const metricsHeaders: string[] = reportData?.metrics_headers || [];

  // Close menu on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false);
      }
    };
    if (menuOpen) document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [menuOpen]);

  const handleSaveRename = () => {
    if (editName.trim() && editName.trim() !== sheet.sheet_name) {
      onRename(sheet.id, editName.trim());
    }
    setEditing(false);
  };

  return (
    <Card className="overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-4 border-b bg-muted/20">
        <div className="flex items-center gap-3 min-w-0">
          {editing ? (
            <div className="flex items-center gap-2">
              <Input
                value={editName}
                onChange={(e) => setEditName(e.target.value)}
                className="h-8 w-64 text-base font-semibold"
                autoFocus
                onKeyDown={(e) => {
                  if (e.key === "Enter") handleSaveRename();
                  if (e.key === "Escape") setEditing(false);
                }}
              />
              <button
                onClick={handleSaveRename}
                className="p-1 hover:bg-muted rounded"
              >
                <Check className="h-4 w-4 text-green-600" />
              </button>
              <button
                onClick={() => setEditing(false)}
                className="p-1 hover:bg-muted rounded"
              >
                <X className="h-4 w-4 text-red-500" />
              </button>
            </div>
          ) : (
            <>
              <h3 className="text-base font-semibold truncate">
                {sheet.sheet_name}
              </h3>
              <button
                onClick={() => {
                  setEditName(sheet.sheet_name);
                  setEditing(true);
                }}
                className="p-1 hover:bg-muted rounded opacity-60 hover:opacity-100 flex-shrink-0"
              >
                <Pencil className="h-3.5 w-3.5" />
              </button>
            </>
          )}

          {/* Sheet info badges */}
          {!editing && (
            <div className="flex items-center gap-2 ml-2">
              <Badge variant="outline" className="text-xs">
                {SHEET_TYPE_LABELS[sheet.sheet_type] || sheet.sheet_type}
              </Badge>
              <span className="text-xs text-muted-foreground flex items-center gap-1">
                <Calendar className="h-3 w-3" />
                {sheet.schedule === "weekly" ? "Weekly" : "Monthly"} &middot;{" "}
                {sheet.duration}{" "}
                {sheet.schedule === "weekly" ? "weeks" : "months"}
              </span>
              <span className="text-xs text-muted-foreground flex items-center gap-1">
                <ArrowUpDown className="h-3 w-3" />
                {sheet.order_by}
              </span>
            </div>
          )}
        </div>

        {/* 3-dot menu */}
        <div className="relative flex-shrink-0" ref={menuRef}>
          <button
            onClick={() => setMenuOpen(!menuOpen)}
            className="p-1.5 hover:bg-muted rounded transition-colors"
          >
            <MoreVertical className="h-4 w-4" />
          </button>
          {menuOpen && (
            <div className="absolute right-0 top-full mt-1 bg-white border rounded-lg shadow-lg z-30 py-1 min-w-[150px]">
              <button
                onClick={() => {
                  setEditing(true);
                  setEditName(sheet.sheet_name);
                  setMenuOpen(false);
                }}
                className="w-full text-left px-4 py-2 text-sm hover:bg-muted flex items-center gap-2"
              >
                <Pencil className="h-3.5 w-3.5" />
                Rename
              </button>
              <button
                onClick={() => {
                  onDelete(sheet.id);
                  setMenuOpen(false);
                }}
                className="w-full text-left px-4 py-2 text-sm text-destructive hover:bg-destructive/10 flex items-center gap-2"
              >
                <Trash2 className="h-3.5 w-3.5" />
                Delete
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Data loading state */}
      {dataLoading && !reportData && (
        <div className="px-5 py-10 flex items-center justify-center">
          <Loader2 className="h-5 w-5 animate-spin text-muted-foreground mr-2" />
          <span className="text-sm text-muted-foreground">Loading report data...</span>
        </div>
      )}

      {/* Error from backend */}
      {errorMsg && (
        <div className="px-5 py-8 text-center">
          <p className="text-sm text-destructive">{errorMsg}</p>
          <p className="text-xs text-muted-foreground mt-1">
            Please connect the required integration in Domain Settings.
          </p>
        </div>
      )}

      {/* API-level error */}
      {dataError && !reportData && !dataLoading && (
        <div className="px-5 py-8 text-center">
          <p className="text-sm text-destructive">
            Unable to load report data. Please try again later.
          </p>
        </div>
      )}

      {/* No data yet (API returned but no rows) */}
      {!dataLoading && reportData && !hasData && !errorMsg && (
        <div className="px-5 py-8 text-center text-muted-foreground text-sm">
          No data found for the selected date ranges. Data may take some time to appear in Google Search Console.
        </div>
      )}

      {/* Waiting for data to load */}
      {!dataLoading && !dataError && !reportData && (
        <div className="px-5 py-8 text-center text-muted-foreground text-sm">
          Loading report data...
        </div>
      )}

      {/* Data Table */}
      {hasData && (
        <>
          {/* Metric group header */}
          {metricsHeaders.length > 0 && (
            <div className="flex items-center justify-center gap-6 px-5 py-2 bg-muted/10 border-b text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              {metricsHeaders.map((mh) => (
                <span key={mh}>{mh}</span>
              ))}
            </div>
          )}

          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b" style={{ backgroundColor: "#f6f9fe" }}>
                  {columns.map((col) => {
                    const isDimCol =
                      col === "Sr No" ||
                      col === "Pages" ||
                      col === "Queries" ||
                      col === "Landing Pages" ||
                      col === "Keywords" ||
                      col === "Source" ||
                      col === "Metric";
                    return (
                      <th
                        key={col}
                        className="px-4 py-3 text-left font-semibold text-xs whitespace-nowrap"
                        style={{
                          minWidth:
                            col === "Sr No"
                              ? 60
                              : isDimCol
                                ? 280
                                : 150,
                          position:
                            col === "Sr No" || isDimCol
                              ? "sticky"
                              : undefined,
                          left:
                            col === "Sr No"
                              ? 0
                              : isDimCol
                                ? (hasSrNo ? 60 : 0)
                                : undefined,
                          backgroundColor: "#f6f9fe",
                          zIndex: isDimCol || col === "Sr No" ? 2 : undefined,
                        }}
                      >
                        {col}
                      </th>
                    );
                  })}
                </tr>
              </thead>
              <tbody>
                {paginatedRows.map((row, rowIdx) => {
                  const bg = rowIdx % 2 === 0 ? "#fff" : "#faf8ff";
                  return (
                    <tr
                      key={rowIdx}
                      className="border-b hover:bg-muted/20 transition-colors"
                      style={{ backgroundColor: bg }}
                    >
                      {columns.map((col) => {
                        const value = row[col];
                        const isChange = col.includes("Change") || col.includes("MOM %") || col.includes("YOY %") || col.includes("WOW %");
                        const isUrl =
                          typeof value === "string" &&
                          (value.startsWith("http://") ||
                            value.startsWith("https://"));
                        const numVal =
                          typeof value === "number"
                            ? value
                            : parseFloat(String(value));
                        const isNegative =
                          isChange && !isNaN(numVal) && numVal < 0;
                        const isPositive =
                          isChange && !isNaN(numVal) && numVal > 0;

                        const isDimCol =
                          col === "Sr No" ||
                          col === "Pages" ||
                          col === "Queries" ||
                          col === "Landing Pages" ||
                          col === "Keywords" ||
                          col === "Source" ||
                          col === "Metric";

                        return (
                          <td
                            key={col}
                            className="px-4 py-3 whitespace-nowrap text-sm"
                            style={{
                              minWidth: col === "Sr No" ? 60 : undefined,
                              position:
                                col === "Sr No" || isDimCol
                                  ? "sticky"
                                  : undefined,
                              left:
                                col === "Sr No"
                                  ? 0
                                  : isDimCol
                                    ? (hasSrNo ? 60 : 0)
                                    : undefined,
                              backgroundColor: bg,
                              zIndex:
                                isDimCol || col === "Sr No" ? 1 : undefined,
                            }}
                          >
                            {isUrl ? (
                              <a
                                href={value}
                                target="_blank"
                                rel="noreferrer"
                                className="text-primary hover:underline truncate block max-w-[260px]"
                                title={value}
                              >
                                {value}
                              </a>
                            ) : isNegative ? (
                              <span className="text-red-500 font-medium">
                                {value}{" "}
                                <span className="text-xs">&#9660;</span>
                              </span>
                            ) : isPositive ? (
                              <span className="text-green-600 font-medium">
                                {value}{" "}
                                <span className="text-xs">&#9650;</span>
                              </span>
                            ) : (
                              <span>{value ?? "-"}</span>
                            )}
                          </td>
                        );
                      })}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          <div className="flex items-center justify-end gap-4 px-5 py-3 border-t text-sm text-muted-foreground">
            <span className="flex items-center gap-1">
              Rows per page:
              <select
                value={rowsPerPage}
                onChange={(e) => {
                  setRowsPerPage(Number(e.target.value));
                  setPage(0);
                }}
                className="ml-1 border rounded px-1 py-0.5 text-sm bg-white cursor-pointer"
              >
                {ROWS_PER_PAGE_OPTIONS.map((opt) => (
                  <option key={opt} value={opt}>{opt}</option>
                ))}
              </select>
            </span>
            <span>
              {page * rowsPerPage + 1}-
              {Math.min((page + 1) * rowsPerPage, totalRows)} of {totalRows}
            </span>
            <div className="flex items-center gap-1">
              <button
                onClick={() => setPage(0)}
                disabled={page === 0}
                className="p-1 hover:bg-muted rounded disabled:opacity-30"
              >
                <ChevronsLeft className="h-4 w-4" />
              </button>
              <button
                onClick={() => setPage(Math.max(0, page - 1))}
                disabled={page === 0}
                className="p-1 hover:bg-muted rounded disabled:opacity-30"
              >
                <ChevronLeft className="h-4 w-4" />
              </button>
              <button
                onClick={() => setPage(Math.min(totalPages - 1, page + 1))}
                disabled={page >= totalPages - 1}
                className="p-1 hover:bg-muted rounded disabled:opacity-30"
              >
                <ChevronRight className="h-4 w-4" />
              </button>
              <button
                onClick={() => setPage(totalPages - 1)}
                disabled={page >= totalPages - 1}
                className="p-1 hover:bg-muted rounded disabled:opacity-30"
              >
                <ChevronsRight className="h-4 w-4" />
              </button>
            </div>
          </div>
        </>
      )}
    </Card>
  );
}

export default SeoReports;
