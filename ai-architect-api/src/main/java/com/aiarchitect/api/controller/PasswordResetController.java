package com.aiarchitect.api.controller;

import com.aiarchitect.api.dto.PasswordResetConfirmDto;
import com.aiarchitect.api.dto.PasswordResetRequestDto;
import com.aiarchitect.api.service.PasswordResetService;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

/**
 * Public endpoints for requesting and completing password resets.
 *
 * All request responses avoid revealing whether an email is registered.
 *
 * @author OpenAI
 */
@RestController
@RequestMapping("/api/v1/auth")
@RequiredArgsConstructor
@Slf4j
public class PasswordResetController {

    private static final String RESET_REQUEST_SUCCESS_MESSAGE =
            "If an account exists for this email address, a password reset link has been sent. The link expires in 30 minutes.";

    private final PasswordResetService passwordResetService;

    /**
     * Requests a password reset email for the supplied address.
     *
     * @param request email request body
     * @param httpRequest servlet request for audit metadata
     * @return the generic success message used for both known and unknown emails
     */
    @PostMapping("/forgot-password")
    public ResponseEntity<Map<String, String>> forgotPassword(
            @Valid @RequestBody PasswordResetRequestDto request,
            HttpServletRequest httpRequest
    ) {
        passwordResetService.requestReset(
                request.email(),
                httpRequest.getRemoteAddr(),
                httpRequest.getHeader("User-Agent")
        );

        return ResponseEntity.ok(Map.of("message", RESET_REQUEST_SUCCESS_MESSAGE));
    }

    /**
     * Completes a password reset using a valid token and new password.
     *
     * @param request reset confirmation body
     * @return success message when the password has been updated
     */
    @PostMapping("/reset-password")
    public ResponseEntity<Map<String, String>> resetPassword(
            @Valid @RequestBody PasswordResetConfirmDto request
    ) {
        if (!request.newPassword().equals(request.confirmPassword())) {
            return ResponseEntity.badRequest().body(Map.of(
                    "error", "password_mismatch",
                    "message", "Passwords do not match."
            ));
        }

        passwordResetService.resetPassword(request.token(), request.newPassword());
        return ResponseEntity.ok(Map.of(
                "message",
                "Your password has been reset. You can now sign in with your new password."
        ));
    }

    /**
     * Checks whether a token is still valid without consuming it.
     *
     * @param token raw token from the reset link
     * @return validity response for the UI
     */
    @GetMapping("/reset-password/validate")
    public ResponseEntity<Map<String, Object>> validateToken(@RequestParam String token) {
        boolean valid = passwordResetService.isTokenValid(token);
        if (valid) {
            return ResponseEntity.ok(Map.of("valid", true));
        }

        return ResponseEntity.status(HttpStatus.GONE).body(Map.of(
                "valid", false,
                "message", "This reset link has expired or has already been used."
        ));
    }
}
