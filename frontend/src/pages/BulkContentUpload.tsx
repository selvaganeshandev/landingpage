import { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useToast } from "@/hooks/use-toast";
import {
  Upload,
  Download,
  FileText,
  ChevronDown,
  Loader2,
  CheckCircle2,
  XCircle,
  Clock,
  Eye,
  RotateCcw,
  ArrowRight,
  ArrowLeft,
  FileSpreadsheet,
  AlertCircle,
  Calendar,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import { apiClient } from "@/services/api";
import { useDomainStore } from "@/stores/domainStore";

interface BulkItem {
  id: number;
  row_number: number;
  content_category: string;
  content_type: string;
  title: string;
  keywords: string;
  article_type: string;
  word_count: number;
  priority: string;
  status: string;
  error_message: string | null;
  retry_count: number;
  generated_content_id: number | null;
  generation_started_at: string | null;
  generation_completed_at: string | null;
}

interface BatchData {
  id: number;
  domain_name: string;
  file_name: string;
  status: string;
  total_items: number;
  processed_items: number;
  successful_items: number;
  failed_items: number;
  error_message: string | null;
  created_at: string;
  completed_at: string | null;
  items: BulkItem[];
}

interface ValidationError {
  row: number;
  errors: string[];
}

const ITEMS_PER_PAGE = 10;

/** Upload formats the page accepts. Extension check is case-insensitive. */
const ACCEPTED_EXTENSIONS = [".xlsx", ".docx"];

const getFileExtension = (fileName: string) =>
  fileName.slice(fileName.lastIndexOf(".")).toLowerCase();

const isAcceptedFile = (fileName: string) =>
  ACCEPTED_EXTENSIONS.includes(getFileExtension(fileName));

/** Word briefs are numbered "Brief N"; Excel rows keep "Row N". */
const errorRowLabel = (fileName: string | undefined, row: number) =>
  fileName && getFileExtension(fileName) === ".docx" ? `Brief ${row}` : `Row ${row}`;

const STATUS_CONFIG: Record<string, { label: string; color: string; icon: any }> = {
  processed: { label: "Queued", color: "bg-muted text-muted-foreground", icon: Clock },
  generating: { label: "Generating", color: "bg-blue-500/10 text-blue-600", icon: Loader2 },
  generated: { label: "Generated", color: "bg-emerald-500/10 text-emerald-600", icon: CheckCircle2 },
  generation_failed: { label: "Failed", color: "bg-red-500/10 text-red-600", icon: XCircle },
  in_review: { label: "In Review", color: "bg-amber-500/10 text-amber-600", icon: Eye },
  approved: { label: "Approved", color: "bg-emerald-500/10 text-emerald-700", icon: CheckCircle2 },
};

const BulkContentUpload = () => {
  const { toast } = useToast();
  const navigate = useNavigate();
  const { selectedDomain } = useDomainStore();
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Upload state
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [isDragOver, setIsDragOver] = useState(false);
  const [validationErrors, setValidationErrors] = useState<ValidationError[]>([]);

  // Batch state
  const [batchData, setBatchData] = useState<BatchData | null>(null);
  const [loadingInitial, setLoadingInitial] = useState(true);
  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // Pagination
  const [currentPage, setCurrentPage] = useState(1);

  const isProcessing = batchData?.status === 'processing';

  const totalItems = batchData?.items?.length || 0;
  const totalPages = Math.max(1, Math.ceil(totalItems / ITEMS_PER_PAGE));
  const startIdx = (currentPage - 1) * ITEMS_PER_PAGE;
  const paginatedItems = batchData?.items?.slice(startIdx, startIdx + ITEMS_PER_PAGE) || [];

  // Reset to page 1 when batch changes
  useEffect(() => {
    setCurrentPage(1);
  }, [batchData?.id]);

  // On mount: check if there's an active processing batch for this domain
  useEffect(() => {
    if (selectedDomain) {
      checkActiveBatch();
    }
    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = null;
      }
    };
  }, [selectedDomain]);

  const checkActiveBatch = async () => {
    if (!selectedDomain) return;
    setLoadingInitial(true);
    try {
      const response: any = await apiClient.getBulkUploadBatches({
        domain_id: String(selectedDomain.id),
      });
      if (response?.data?.length) {
        const processingBatch = response.data.find(
          (b: any) => b.status === 'processing'
        );
        if (processingBatch) {
          await loadBatchDetail(processingBatch.id);
          startPolling(processingBatch.id);
        }
      }
    } catch (err) {
      console.error("Failed to check active batch:", err);
    } finally {
      setLoadingInitial(false);
    }
  };

  const loadBatchDetail = async (batchId: number) => {
    try {
      const response: any = await apiClient.getBulkUploadBatchDetail(batchId);
      if (response?.data) {
        setBatchData(response.data);
        return response.data;
      }
    } catch (err) {
      console.error("Failed to load batch detail:", err);
    }
    return null;
  };

  const startPolling = (batchId: number) => {
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
    }
    pollIntervalRef.current = setInterval(async () => {
      try {
        const response: any = await apiClient.getBulkUploadBatchDetail(batchId);
        if (response?.data) {
          setBatchData(response.data);

          const terminalStatuses = ['completed', 'completed_with_errors', 'failed'];
          if (terminalStatuses.includes(response.data.status)) {
            if (pollIntervalRef.current) {
              clearInterval(pollIntervalRef.current);
              pollIntervalRef.current = null;
            }
          }
        }
      } catch (err) {
        console.error("Poll error:", err);
      }
    }, 5000);
  };

  const handleDownloadTemplate = async () => {
    try {
      await apiClient.downloadBulkUploadTemplate(selectedDomain?.id);
      toast({ title: "Template downloaded", description: "Fill in the template and upload it back." });
    } catch {
      toast({ title: "Download failed", variant: "destructive" });
    }
  };

  const handleDownloadDocxTemplate = async () => {
    try {
      await apiClient.downloadBulkUploadDocxTemplate(selectedDomain?.id);
      toast({ title: "Template downloaded", description: "Fill in one table per brief and upload it back." });
    } catch {
      toast({ title: "Download failed", variant: "destructive" });
    }
  };

  const acceptFile = (file: File) => {
    if (!isAcceptedFile(file.name)) {
      toast({
        title: "Invalid file",
        description: "Only .xlsx and .docx files are supported",
        variant: "destructive",
      });
      return;
    }
    setValidationErrors([]);
    setSelectedFile(file);
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) acceptFile(file);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    const file = e.dataTransfer.files?.[0];
    if (file) acceptFile(file);
  };

  const handleUpload = async () => {
    if (!selectedFile || !selectedDomain || isProcessing) return;

    setUploading(true);
    setValidationErrors([]);
    const isDocx = getFileExtension(selectedFile.name) === ".docx";
    try {
      const upload = isDocx
        ? apiClient.uploadBulkContentDocx
        : apiClient.uploadBulkContent;
      const response: any = await upload(Number(selectedDomain.id), selectedFile);

      if (response?.data?.id) {
        const newBatchId = response.data.id;
        setBatchData(response.data);
        setSelectedFile(null);
        setCurrentPage(1);

        startPolling(newBatchId);

        toast({
          title: "Upload successful",
          description: `${response.data.total_items} items queued. Generation started automatically.`,
        });
      }
    } catch (err: any) {
      const errorData = err?.response;
      if (errorData?.validation_errors) {
        const errorCount = errorData.validation_errors.length;
        const unit = isDocx ? "brief" : "row";
        // Keep every error on the page — the toast only summarises.
        setValidationErrors(errorData.validation_errors);
        toast({
          title: `Validation failed (${errorCount} ${unit}${errorCount > 1 ? 's' : ''})`,
          description: "Nothing was imported. See the details below.",
          variant: "destructive",
        });
      } else {
        toast({
          title: "Upload failed",
          description: errorData?.message || "An error occurred",
          variant: "destructive",
        });
      }
    } finally {
      setUploading(false);
    }
  };

  const handleRetry = async (itemId: number) => {
    if (!batchData) return;
    try {
      await apiClient.retryBulkUploadItem(itemId);
      toast({ title: "Retry started" });
      await loadBatchDetail(batchData.id);
    } catch {
      toast({ title: "Retry failed", variant: "destructive" });
    }
  };

  const handleStatusUpdate = async (itemId: number, newStatus: string) => {
    if (!batchData) return;
    try {
      await apiClient.updateBulkUploadItemStatus(itemId, newStatus);
      await loadBatchDetail(batchData.id);
    } catch {
      toast({ title: "Status update failed", variant: "destructive" });
    }
  };

  const handleViewContent = (contentId: number) => {
    navigate(`/content-editor/${contentId}`);
  };

  const progressPercent = batchData
    ? Math.round((batchData.processed_items / Math.max(batchData.total_items, 1)) * 100)
    : 0;

  const batchDone = batchData && ['completed', 'completed_with_errors', 'failed'].includes(batchData.status);

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  if (loadingInitial) {
    return (
      <div className="p-8 flex items-center justify-center min-h-[400px]">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="p-8 space-y-6 bg-background animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => navigate('/content-calendar')}
            className="h-8 px-2"
          >
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Bulk Content Upload</h1>
            <p className="text-sm text-muted-foreground">
              Upload Excel template to generate multiple content items at once
            </p>
          </div>
        </div>
        <Button
          variant="outline"
          onClick={() => navigate('/content-calendar')}
          className="border-border/50"
        >
          <Calendar className="h-4 w-4 mr-2" />
          Content Planner
        </Button>
      </div>

      {/* Upload Section */}
      <Card className="border border-border p-5">
        {/* Row 1: Title + Download Template */}
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-primary/20 to-primary/5 flex items-center justify-center">
              <FileSpreadsheet className="h-4.5 w-4.5 text-primary" />
            </div>
            <div>
              <h3 className="text-base font-semibold">Upload Content</h3>
              <p className="text-xs text-muted-foreground">Fill in the Excel or Word template and upload to auto-generate content</p>
            </div>
          </div>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" size="sm">
                <Download className="h-4 w-4 mr-2" />
                Download Template
                <ChevronDown className="h-3.5 w-3.5 ml-2 opacity-70" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-56">
              <DropdownMenuItem onClick={handleDownloadTemplate} className="gap-2">
                <FileSpreadsheet className="h-4 w-4 text-emerald-600" />
                <div className="flex flex-col">
                  <span className="text-sm">Excel Template</span>
                  <span className="text-xs text-muted-foreground">.xlsx — one row per article</span>
                </div>
              </DropdownMenuItem>
              <DropdownMenuItem onClick={handleDownloadDocxTemplate} className="gap-2">
                <FileText className="h-4 w-4 text-blue-600" />
                <div className="flex flex-col">
                  <span className="text-sm">Word Template</span>
                  <span className="text-xs text-muted-foreground">.docx — one table per brief</span>
                </div>
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>

        {/* Row 2: Drop zone (100px height) */}
        <input
          type="file"
          ref={fileInputRef}
          accept=".xlsx,.docx"
          onChange={handleFileSelect}
          className="hidden"
          disabled={isProcessing}
        />
        <div
          onClick={() => !isProcessing && fileInputRef.current?.click()}
          onDragOver={(e) => { e.preventDefault(); if (!isProcessing) setIsDragOver(true); }}
          onDragLeave={() => setIsDragOver(false)}
          onDrop={(e) => { if (isProcessing) { e.preventDefault(); return; } handleDrop(e); }}
          style={{ height: 100 }}
          className={`w-full border-2 border-dashed rounded-lg px-4 flex items-center justify-center transition-all ${
            isProcessing
              ? 'border-border bg-muted/30 cursor-not-allowed opacity-50'
              : isDragOver
                ? 'border-primary bg-primary/5 cursor-pointer'
                : selectedFile
                  ? 'border-emerald-400 bg-emerald-50/80 dark:bg-emerald-500/5 cursor-pointer'
                  : 'border-border hover:border-primary/40 hover:bg-muted/20 cursor-pointer'
          }`}
        >
          {selectedFile ? (
            <div className="flex flex-col items-center gap-1">
              {getFileExtension(selectedFile.name) === ".docx" ? (
                <FileText className="h-5 w-5 text-blue-600" />
              ) : (
                <FileSpreadsheet className="h-5 w-5 text-emerald-600" />
              )}
              <span className="font-medium text-sm text-emerald-700 dark:text-emerald-400 truncate">
                {selectedFile.name}
              </span>
              <span className="text-xs text-muted-foreground">
                {(selectedFile.size / 1024).toFixed(1)} KB —{" "}
                {getFileExtension(selectedFile.name) === ".docx" ? "Word" : "Excel"} — Ready to upload
              </span>
            </div>
          ) : (
            <div className="flex flex-col items-center gap-1">
              <Upload className="h-5 w-5 text-muted-foreground" />
              <span className="text-sm text-muted-foreground">
                Drop <span className="font-medium text-foreground">.xlsx</span> or{" "}
                <span className="font-medium text-foreground">.docx</span> file here or click to browse
              </span>
            </div>
          )}
        </div>

        {/* Row 3: Upload button centered */}
        <div className="flex justify-center mt-4">
          <Button
            onClick={handleUpload}
            disabled={!selectedFile || uploading || !selectedDomain || isProcessing}
            className="gradient-primary shadow-md shadow-primary/25 px-8"
          >
            {uploading ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Uploading...
              </>
            ) : (
              <>
                <Upload className="h-4 w-4 mr-2" />
                Upload & Start Generation
              </>
            )}
          </Button>
        </div>

        {/* Processing banner */}
        {isProcessing && (
          <div className="flex items-center gap-2 text-xs text-blue-600 bg-blue-500/10 rounded-md px-3 py-2 mt-3">
            <Loader2 className="h-3.5 w-3.5 animate-spin flex-shrink-0" />
            <span>A batch is currently processing. Upload will be available once it completes.</span>
          </div>
        )}

        {/* Validation errors — every error, not just the first few */}
        {validationErrors.length > 0 && (
          <div className="mt-4 rounded-lg border border-red-200 dark:border-red-500/30 bg-red-50/60 dark:bg-red-500/5 overflow-hidden">
            <div className="flex items-start gap-2 px-3 py-2.5 border-b border-red-200 dark:border-red-500/30">
              <AlertCircle className="h-4 w-4 text-red-600 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-sm font-medium text-red-700 dark:text-red-400">
                  {validationErrors.length} problem{validationErrors.length > 1 ? 's' : ''} found — nothing was imported
                </p>
                <p className="text-xs text-muted-foreground">
                  Fix these in your file and upload it again.
                </p>
              </div>
            </div>
            <div className="max-h-56 overflow-y-auto divide-y divide-red-200/60 dark:divide-red-500/20">
              {validationErrors.map((entry) => (
                <div key={entry.row} className="flex gap-3 px-3 py-2">
                  <span className="text-xs font-medium text-red-700 dark:text-red-400 whitespace-nowrap pt-0.5">
                    {errorRowLabel(selectedFile?.name, entry.row)}
                  </span>
                  <ul className="text-xs text-muted-foreground space-y-0.5">
                    {entry.errors.map((message, i) => (
                      <li key={i}>{message}</li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          </div>
        )}
      </Card>

      {/* Batch Detail + Items Table */}
      {batchData && (
        <Card className="border border-border overflow-hidden">
          {/* Batch header */}
          <div className="px-5 py-4 border-b border-border bg-muted/20">
            <div className="flex items-center justify-between mb-3">
              <div>
                <h3 className="text-base font-semibold">{batchData.file_name}</h3>
                <p className="text-xs text-muted-foreground">
                  Uploaded {formatDate(batchData.created_at)}
                </p>
              </div>
              <div className="flex gap-2">
                <Badge variant="outline" className="bg-emerald-500/10 text-emerald-600 border-emerald-200">
                  {batchData.successful_items} Generated
                </Badge>
                {batchData.failed_items > 0 && (
                  <Badge variant="outline" className="bg-red-500/10 text-red-600 border-red-200">
                    {batchData.failed_items} Failed
                  </Badge>
                )}
                {isProcessing && (
                  <Badge variant="outline" className="bg-blue-500/10 text-blue-600 border-blue-200">
                    <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                    Processing
                  </Badge>
                )}
              </div>
            </div>

            {/* Progress bar */}
            <div className="space-y-1">
              <div className="flex justify-between text-xs text-muted-foreground">
                <span>{batchData.processed_items} of {batchData.total_items} processed</span>
                <span>{progressPercent}%</span>
              </div>
              <Progress value={progressPercent} className="h-2" />
            </div>

            {/* Batch completion message */}
            {batchDone && (
              <div className="mt-2.5 flex items-center gap-2 text-sm">
                {batchData.status === 'completed' && (
                  <>
                    <CheckCircle2 className="h-4 w-4 text-emerald-500" />
                    <span className="text-emerald-600">All {batchData.total_items} items generated successfully</span>
                  </>
                )}
                {batchData.status === 'completed_with_errors' && (
                  <>
                    <AlertCircle className="h-4 w-4 text-amber-500" />
                    <span className="text-amber-600">
                      {batchData.successful_items} generated, {batchData.failed_items} failed — retry failed items below
                    </span>
                  </>
                )}
                {batchData.status === 'failed' && (
                  <>
                    <XCircle className="h-4 w-4 text-red-500" />
                    <span className="text-red-600">Batch failed: {batchData.error_message}</span>
                  </>
                )}
              </div>
            )}
          </div>

          {/* Items table */}
          <Table>
            <TableHeader>
              <TableRow className="bg-muted/50">
                <TableHead className="w-[50px]">#</TableHead>
                <TableHead className="min-w-[250px]">Title / Page Title / Topic</TableHead>
                <TableHead>Category</TableHead>
                <TableHead>Type</TableHead>
                <TableHead className="w-[80px]">Words</TableHead>
                <TableHead className="w-[90px]">Priority</TableHead>
                <TableHead className="w-[140px]">Status</TableHead>
                <TableHead className="w-[200px]">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {paginatedItems.map((item) => {
                const statusConfig = STATUS_CONFIG[item.status] || STATUS_CONFIG.processed;
                const StatusIcon = statusConfig.icon;

                return (
                  <TableRow key={item.id}>
                    <TableCell className="font-mono text-xs text-muted-foreground">
                      {item.row_number}
                    </TableCell>
                    <TableCell>
                      <div>
                        <p className="font-medium text-sm truncate max-w-[300px]">
                          {item.title}
                        </p>
                        <p className="text-xs text-muted-foreground truncate max-w-[300px]">
                          {item.keywords}
                        </p>
                      </div>
                    </TableCell>
                    <TableCell>
                      <span className="text-xs">{item.content_category}</span>
                    </TableCell>
                    <TableCell>
                      <span className="text-xs">{item.content_type}</span>
                    </TableCell>
                    <TableCell>
                      <span className="text-xs">{item.word_count}</span>
                    </TableCell>
                    <TableCell>
                      <Badge
                        variant="outline"
                        className={`text-[10px] ${
                          item.priority === 'high'
                            ? 'bg-red-500/10 text-red-600 border-red-200'
                            : item.priority === 'medium'
                              ? 'bg-amber-500/10 text-amber-600 border-amber-200'
                              : 'bg-muted text-muted-foreground'
                        }`}
                      >
                        {item.priority}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Badge className={`${statusConfig.color} border-0 gap-1`}>
                        <StatusIcon className={`h-3 w-3 ${item.status === 'generating' ? 'animate-spin' : ''}`} />
                        {statusConfig.label}
                      </Badge>
                      {item.status === 'generation_failed' && item.error_message && (
                        <p
                          className="text-[10px] text-red-500 mt-1 truncate max-w-[130px]"
                          title={item.error_message}
                        >
                          {item.error_message}
                        </p>
                      )}
                    </TableCell>
                    <TableCell>
                      <div className="flex gap-1.5 flex-wrap">
                        {item.status === 'generated' && (
                          <>
                            {item.generated_content_id && (
                              <Button
                                size="sm"
                                variant="outline"
                                className="h-7 text-xs"
                                onClick={() => handleViewContent(item.generated_content_id!)}
                              >
                                <Eye className="h-3 w-3 mr-1" />
                                View
                              </Button>
                            )}
                            <Button
                              size="sm"
                              variant="outline"
                              className="h-7 text-xs"
                              onClick={() => handleStatusUpdate(item.id, 'in_review')}
                            >
                              <ArrowRight className="h-3 w-3 mr-1" />
                              To Review
                            </Button>
                          </>
                        )}
                        {item.status === 'generation_failed' && (
                          <Button
                            size="sm"
                            variant="outline"
                            className="h-7 text-xs text-amber-600 hover:text-amber-700"
                            onClick={() => handleRetry(item.id)}
                          >
                            <RotateCcw className="h-3 w-3 mr-1" />
                            Retry
                          </Button>
                        )}
                        {item.status === 'in_review' && (
                          <>
                            {item.generated_content_id && (
                              <Button
                                size="sm"
                                variant="ghost"
                                className="h-7 text-xs"
                                onClick={() => handleViewContent(item.generated_content_id!)}
                              >
                                <Eye className="h-3 w-3" />
                              </Button>
                            )}
                            <Button
                              size="sm"
                              className="h-7 text-xs bg-emerald-600 hover:bg-emerald-700 text-white"
                              onClick={() => handleStatusUpdate(item.id, 'approved')}
                            >
                              <CheckCircle2 className="h-3 w-3 mr-1" />
                              Approve
                            </Button>
                          </>
                        )}
                        {item.status === 'approved' && item.generated_content_id && (
                          <Button
                            size="sm"
                            variant="outline"
                            className="h-7 text-xs"
                            onClick={() => handleViewContent(item.generated_content_id!)}
                          >
                            <Eye className="h-3 w-3 mr-1" />
                            View
                          </Button>
                        )}
                      </div>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>

          {/* Pagination */}
          {totalItems > ITEMS_PER_PAGE && (
            <div className="px-5 py-3 border-t border-border bg-muted/10 flex items-center justify-between">
              <p className="text-xs text-muted-foreground">
                Showing {startIdx + 1}–{Math.min(startIdx + ITEMS_PER_PAGE, totalItems)} of {totalItems} items
              </p>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  className="h-8 px-3"
                  disabled={currentPage <= 1}
                  onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                >
                  <ChevronLeft className="h-4 w-4 mr-1" />
                  Prev
                </Button>
                <span className="text-sm text-muted-foreground tabular-nums">
                  Page {currentPage} of {totalPages}
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  className="h-8 px-3"
                  disabled={currentPage >= totalPages}
                  onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                >
                  Next
                  <ChevronRight className="h-4 w-4 ml-1" />
                </Button>
              </div>
            </div>
          )}
        </Card>
      )}
    </div>
  );
};

export default BulkContentUpload;
