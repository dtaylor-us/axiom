package com.archon.api.config;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.slf4j.MDC;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;

/**
 * Adds the conversation ID from the request path to the SLF4J MDC
 * so that every log line within a chat request includes the conversation
 * for easy correlation in Jaeger / log aggregation.
 *
 * <p>Runs early in the filter chain (after security but before controllers).</p>
 */
@Component
@Order(Ordered.HIGHEST_PRECEDENCE + 10)
public class MdcConversationFilter extends OncePerRequestFilter {

    private static final String MDC_KEY = "conversationId";

    @Override
    protected void doFilterInternal(
            HttpServletRequest request,
            HttpServletResponse response,
            FilterChain chain) throws ServletException, IOException {

        String conversationId = extractConversationId(request);
        if (conversationId != null) {
            MDC.put(MDC_KEY, conversationId);
        }
        try {
            chain.doFilter(request, response);
        } finally {
            MDC.remove(MDC_KEY);
        }
    }

    /**
     * Extracts the conversation UUID from chat endpoint paths.
     * Expected pattern: /api/conversations/{id}/chat
     */
    private String extractConversationId(HttpServletRequest request) {
        String path = request.getRequestURI();
        if (path != null && path.contains("/conversations/")) {
            String[] parts = path.split("/conversations/");
            if (parts.length > 1) {
                String tail = parts[1];
                int slash = tail.indexOf('/');
                return slash > 0 ? tail.substring(0, slash) : tail;
            }
        }
        return null;
    }
}
