import { apiClient } from './api'
import type {
  ReportConfiguration,
  ReportConfigurationRequest,
  WeeklyReport,
  CustomReportRequest,
  CustomReport,
  ReportHistory
} from '@/types/reports'

export class ReportsService {
  /**
   * Configure weekly reports for a business
   */
  async configureWeeklyReports(
    businessId: string,
    config: ReportConfigurationRequest
  ): Promise<ReportConfiguration> {
    const response = await apiClient.post<ReportConfiguration>(
      `/reports/${businessId}/configuration`,
      config
    )
    return response.data
  }

  /**
   * Get current report configuration for a business
   */
  async getReportConfiguration(businessId: string): Promise<ReportConfiguration | null> {
    try {
      const response = await apiClient.get<ReportConfiguration>(
        `/reports/${businessId}/configuration`
      )
      return response.data
    } catch (error: any) {
      if (error.response?.status === 404) {
        return null
      }
      throw error
    }
  }

  /**
   * Update report configuration for a business
   */
  async updateReportConfiguration(
    businessId: string,
    config: ReportConfigurationRequest
  ): Promise<ReportConfiguration> {
    const response = await apiClient.put<ReportConfiguration>(
      `/reports/${businessId}/configuration`,
      config
    )
    return response.data
  }

  /**
   * Generate weekly report for a business
   */
  async generateWeeklyReport(
    businessId: string,
    forceRegenerate: boolean = false
  ): Promise<WeeklyReport> {
    const response = await apiClient.post<WeeklyReport>(
      `/reports/${businessId}/generate-weekly`,
      {},
      {
        params: { force_regenerate: forceRegenerate }
      }
    )
    return response.data
  }

  /**
   * Get historical weekly reports for a business
   */
  async getWeeklyReports(
    businessId: string,
    skip: number = 0,
    limit: number = 10
  ): Promise<WeeklyReport[]> {
    const response = await apiClient.get<WeeklyReport[]>(
      `/reports/${businessId}/weekly`,
      {
        params: { skip, limit }
      }
    )
    return response.data
  }

  /**
   * Get a specific weekly report
   */
  async getWeeklyReport(businessId: string, reportId: string): Promise<WeeklyReport> {
    const response = await apiClient.get<WeeklyReport>(
      `/reports/${businessId}/weekly/${reportId}`
    )
    return response.data
  }

  /**
   * Generate custom report
   */
  async generateCustomReport(
    businessId: string,
    request: CustomReportRequest
  ): Promise<CustomReport> {
    const response = await apiClient.post<CustomReport>(
      `/reports/${businessId}/custom`,
      request
    )
    return response.data
  }

  /**
   * Send report via email
   */
  async sendReportEmail(
    businessId: string,
    reportId: string,
    recipientEmail?: string
  ): Promise<{ message: string; recipient: string; report_id: string }> {
    const response = await apiClient.post(
      `/reports/${businessId}/email/${reportId}`,
      {},
      {
        params: recipientEmail ? { recipient_email: recipientEmail } : {}
      }
    )
    return response.data
  }

  /**
   * Delete a weekly report (Admin+ only)
   */
  async deleteWeeklyReport(businessId: string, reportId: string): Promise<void> {
    await apiClient.delete(`/reports/${businessId}/weekly/${reportId}`)
  }

  /**
   * Download report as PDF (if implemented)
   */
  async downloadReport(businessId: string, reportId: string): Promise<Blob> {
    const response = await apiClient.get(
      `/reports/${businessId}/weekly/${reportId}/download`,
      {
        responseType: 'blob'
      }
    )
    return response.data
  }
}

export const reportsService = new ReportsService()