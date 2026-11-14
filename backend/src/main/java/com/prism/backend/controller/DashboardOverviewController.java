package com.prism.backend.controller;

import com.prism.backend.dto.api.ApiResponseEnvelope;
import com.prism.backend.dto.dashboard.DashboardOverviewResponse;
import com.prism.backend.service.dashboard.DashboardOverviewService;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.UUID;

@RestController
@RequestMapping("/api/v1/dashboard")
public class DashboardOverviewController extends BaseController {

    private final DashboardOverviewService dashboardOverviewService;

    public DashboardOverviewController(
            DashboardOverviewService dashboardOverviewService
    ) {
        this.dashboardOverviewService = dashboardOverviewService;
    }

    @GetMapping("/overview")
    public ApiResponseEnvelope<DashboardOverviewResponse> getOverview(
            @RequestHeader(value = "Request-ID", required = false)
            String requestId
    ) {
        String resolvedRequestId = requestId == null || requestId.isBlank()
                ? UUID.randomUUID().toString()
                : requestId.trim();

        return success(
                resolvedRequestId,
                dashboardOverviewService.getOverview()
        );
    }
}
