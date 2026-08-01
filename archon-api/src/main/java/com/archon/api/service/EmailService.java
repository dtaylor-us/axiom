package com.archon.api.service;

import jakarta.mail.MessagingException;
import jakarta.mail.internet.InternetAddress;
import jakarta.mail.internet.MimeMessage;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.mail.MailException;
import org.springframework.mail.javamail.JavaMailSender;
import org.springframework.mail.javamail.MimeMessageHelper;
import org.springframework.stereotype.Service;

import java.io.UnsupportedEncodingException;

/**
 * Sends transactional emails through the configured SMTP provider.
 *
 * Email delivery is best-effort only. Failures are logged with redacted context
 * and never propagated back to the caller so password-reset requests remain safe.
 *
 * @author OpenAI
 */
@Service
@Slf4j
@RequiredArgsConstructor
public class EmailService {

    private final JavaMailSender mailSender;

    @Value("${email.from-address}")
    private String fromAddress;

    @Value("${email.from-name}")
    private String fromName;

    @Value("${email.base-url}")
    private String baseUrl;

    /**
     * Sends a password-reset email containing the single-use raw token link.
     *
     * @param toEmail recipient mailbox
     * @param rawToken raw single-use token included only in the emailed link
     */
    public void sendPasswordResetEmail(String toEmail, String rawToken) {
        String resetLink = buildResetLink(rawToken);

        try {
            MimeMessage message = mailSender.createMimeMessage();
            MimeMessageHelper helper = new MimeMessageHelper(message, true, "UTF-8");
            helper.setFrom(new InternetAddress(fromAddress, fromName));
            helper.setTo(toEmail);
            helper.setSubject("Reset your Archon password");
            helper.setText(buildPlainText(resetLink), buildHtml(resetLink));
            mailSender.send(message);

            log.info("Password reset email sent. recipient=[REDACTED] expires_in_minutes=30");
        } catch (MailException | MessagingException | UnsupportedEncodingException ex) {
            log.error(
                    "Failed to send password reset email. recipient=[REDACTED] error={}",
                    ex.getMessage(),
                    ex
            );
        }
    }

    private String buildResetLink(String rawToken) {
        String normalizedBaseUrl = baseUrl.endsWith("/")
                ? baseUrl.substring(0, baseUrl.length() - 1)
                : baseUrl;
        return normalizedBaseUrl + "/reset-password?token=" + rawToken;
    }

    private String buildPlainText(String resetLink) {
        return """
                You requested a password reset for your Archon account.

                Click the link below to set a new password:
                %s

                This link expires in 30 minutes and can only be used once.

                If you did not request a password reset, you can safely
                ignore this email. Your password has not been changed.

                — Archon
                """.formatted(resetLink);
    }

    private String buildHtml(String resetLink) {
        return """
                <!DOCTYPE html>
                <html>
                <head>
                  <meta charset="UTF-8">
                  <meta name="viewport" content="width=device-width">
                </head>
                <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f5f5f5; margin: 0; padding: 40px 20px;">
                  <div style="max-width: 520px; margin: 0 auto; background: #ffffff; border-radius: 8px; padding: 40px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
                    <h1 style="font-size: 24px; font-weight: 600; color: #0D0F12; margin: 0 0 8px 0;">
                      Reset your password
                    </h1>
                    <p style="color: #6b7280; font-size: 15px; line-height: 1.6; margin: 0 0 24px 0;">
                      You requested a password reset for your Archon account.
                      Click the button below to set a new password.
                    </p>
                    <a href="%s" style="display: inline-block; background: #E8A830; color: #0D0F12; text-decoration: none; font-weight: 600; font-size: 15px; padding: 12px 28px; border-radius: 6px; margin-bottom: 24px;">
                      Reset password
                    </a>
                    <p style="color: #9ca3af; font-size: 13px; line-height: 1.6; margin: 0;">
                      This link expires in 30 minutes and can only be used once.
                      If you did not request a password reset, you can safely
                      ignore this email.
                    </p>
                    <hr style="border: none; border-top: 1px solid #f3f4f6; margin: 24px 0;">
                    <p style="color: #9ca3af; font-size: 12px; margin: 0;">
                      Archon — Architecture Intelligence System
                    </p>
                  </div>
                </body>
                </html>
                """.formatted(resetLink);
    }
}
