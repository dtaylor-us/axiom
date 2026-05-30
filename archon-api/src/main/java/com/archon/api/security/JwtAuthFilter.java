package com.archon.api.security;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import lombok.RequiredArgsConstructor;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.util.List;

/**
 * JWT Authentication Filter for processing and validating JWT tokens in HTTP requests.
 * 
 * This filter extends {@link OncePerRequestFilter} to ensure that JWT token validation
 * is performed exactly once per request. It intercepts incoming HTTP requests to extract
 * and validate JWT bearer tokens from the Authorization header.
 * 
 * <p>The filter performs the following operations:
 * <ul>
 *   <li>Extracts the JWT token from the "Authorization" header (expects "Bearer " prefix)</li>
 *   <li>Extracts the subject (typically username/user ID) from the JWT token</li>
 *   <li>If a valid subject is found, creates an authentication token and sets it in the SecurityContext</li>
 *   <li>Allows the request to proceed through the filter chain</li>
 * </ul>
 * </p>
 * 
 * <p>This component is automatically registered as a Spring Bean and will be invoked
 * for every HTTP request processed by the application.
 * </p>
 * 
 * @see OncePerRequestFilter
 * @see JwtService
 * @see SecurityContextHolder
 */
@Component
@RequiredArgsConstructor
public class JwtAuthFilter extends OncePerRequestFilter {

    private final JwtService jwtService;

    @Override
    protected void doFilterInternal(
            HttpServletRequest request,
            HttpServletResponse response,
            FilterChain filterChain) throws ServletException, IOException {

        String header = request.getHeader("Authorization");
        if (header != null && header.startsWith("Bearer ")) {
            String token = header.substring(7);
            String subject = jwtService.extractSubject(token);
            if (subject != null) {
                var auth = new UsernamePasswordAuthenticationToken(
                        subject, null, List.of());
                SecurityContextHolder.getContext().setAuthentication(auth);
            }
        }

        filterChain.doFilter(request, response);
    }
}
