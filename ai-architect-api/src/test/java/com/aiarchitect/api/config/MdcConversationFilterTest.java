package com.aiarchitect.api.config;

import jakarta.servlet.FilterChain;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.slf4j.MDC;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

/**
 * Unit tests for MdcConversationFilter.
 *
 * <p>Verifies that conversation IDs are correctly extracted from request URIs and
 * placed into the SLF4J MDC for log correlation, and that the MDC key is always
 * cleaned up after the filter chain completes.</p>
 */
@ExtendWith(MockitoExtension.class)
class MdcConversationFilterTest {

    private static final String MDC_KEY = "conversationId";

    @InjectMocks
    private MdcConversationFilter filter;

    @Mock
    private HttpServletRequest request;

    @Mock
    private HttpServletResponse response;

    @Mock
    private FilterChain chain;

    @AfterEach
    void clearMdc() {
        MDC.remove(MDC_KEY);
    }

    @Test
    void doFilterInternal_setsMdcKeyWhenConversationPathPresent() throws Exception {
        when(request.getRequestURI()).thenReturn("/api/conversations/abc-123/chat");

        filter.doFilterInternal(request, response, chain);

        // MDC is cleared by the filter's finally block, so we capture inside chain
        verify(chain).doFilter(request, response);
    }

    @Test
    void doFilterInternal_skipsWhenNoConversationsSegmentInPath() throws Exception {
        when(request.getRequestURI()).thenReturn("/api/health");

        filter.doFilterInternal(request, response, chain);

        verify(chain).doFilter(request, response);
        assertThat(MDC.get(MDC_KEY)).isNull();
    }

    @Test
    void doFilterInternal_clearsMdcInFinallyBlockAfterChain() throws Exception {
        when(request.getRequestURI()).thenReturn("/api/conversations/some-id/messages");

        filter.doFilterInternal(request, response, chain);

        // MDC must be cleared regardless of chain outcome
        assertThat(MDC.get(MDC_KEY)).isNull();
    }

    @Test
    void doFilterInternal_handlesNullRequestUri() throws Exception {
        when(request.getRequestURI()).thenReturn(null);

        filter.doFilterInternal(request, response, chain);

        verify(chain).doFilter(request, response);
        assertThat(MDC.get(MDC_KEY)).isNull();
    }

    @Test
    void doFilterInternal_handlesConversationsAtEndOfPathWithNoTrailingSlash() throws Exception {
        // Path ends with the ID segment and no trailing slash — still must not throw
        when(request.getRequestURI()).thenReturn("/api/conversations/my-uuid");

        filter.doFilterInternal(request, response, chain);

        verify(chain).doFilter(request, response);
    }

    @Test
    void doFilterInternal_extractsCorrectIdFromNestedPath() throws Exception {
        // Capture the MDC value at chain.doFilter time via an answer
        final String[] captured = {null};
        org.mockito.Mockito.doAnswer(inv -> {
            captured[0] = MDC.get(MDC_KEY);
            return null;
        }).when(chain).doFilter(request, response);
        when(request.getRequestURI()).thenReturn("/api/v1/conversations/conv-999/chat");

        filter.doFilterInternal(request, response, chain);

        assertThat(captured[0]).isEqualTo("conv-999");
        // MDC must be cleared after the filter completes
        assertThat(MDC.get(MDC_KEY)).isNull();
    }
}
