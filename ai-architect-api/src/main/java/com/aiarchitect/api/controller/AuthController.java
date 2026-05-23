package com.aiarchitect.api.controller;

import com.aiarchitect.api.domain.model.User;
import com.aiarchitect.api.domain.repository.UserRepository;
import com.aiarchitect.api.dto.AuthRequest;
import com.aiarchitect.api.dto.AuthResponse;
import com.aiarchitect.api.dto.TokenRequest;
import com.aiarchitect.api.security.JwtService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpStatus;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.server.ResponseStatusException;

/**
 * REST controller for handling user authentication operations.
 * Provides endpoints for user registration and login.
 */
@RestController
@RequestMapping("/api/v1/auth")
@RequiredArgsConstructor
@Slf4j
public class AuthController {

        private final UserRepository userRepository;
        private final JwtService jwtService;
        private final PasswordEncoder passwordEncoder;

        /**
         * Registers a new user with email, password, and name.
         * Throws CONFLICT if email already exists.
         */
        @PostMapping("/register")
        @ResponseStatus(HttpStatus.CREATED)
        public AuthResponse register(@RequestBody @Valid AuthRequest request) {
                // Check if email already registered
                if (userRepository.existsByEmail(request.getEmail())) {
                        throw new ResponseStatusException(
                                        HttpStatus.CONFLICT, "Email already registered");
                }

                // Create and save new user with encoded password
                User user = userRepository.save(User.builder()
                                .email(request.getEmail())
                                .password(passwordEncoder.encode(request.getPassword()))
                                .name(request.getName())
                                .build());

                // Generate JWT token for the new user
                String token = jwtService.generateToken(user.getEmail());
                log.info("User registered: {}", user.getEmail());

                return AuthResponse.builder()
                                .token(token)
                                .email(user.getEmail())
                                .build();
        }

        /**
         * Simplified auto-authentication endpoint.
         * Finds or creates a user by username and returns a JWT token.
         * Used by the UI for seamless auto-login (no password required).
         */
        @PostMapping("/token")
        public AuthResponse token(@RequestBody @Valid TokenRequest request) {
                String syntheticEmail = request.getUsername().toLowerCase().replaceAll("\\s+", ".") + "@auto.local";

                User user = userRepository.findByEmail(syntheticEmail)
                                .orElseGet(() -> userRepository.save(User.builder()
                                                .email(syntheticEmail)
                                                .password(passwordEncoder.encode("auto-" + System.currentTimeMillis()))
                                                .name(request.getUsername())
                                                .build()));

                String token = jwtService.generateToken(user.getEmail());
                log.info("Auto-auth token issued for: {}", user.getEmail());

                return AuthResponse.builder()
                                .token(token)
                                .email(user.getEmail())
                                .build();
        }

        /**
         * Authenticates a user by email and password.
         * Validates credentials and account status before issuing token.
         */
        @PostMapping("/login")
        public AuthResponse login(@RequestBody @Valid AuthRequest request) {
                // Find user by email or throw UNAUTHORIZED
                User user = userRepository.findByEmail(request.getEmail())
                                .orElseThrow(() -> new ResponseStatusException(
                                                HttpStatus.UNAUTHORIZED, "Invalid credentials"));

                // Verify password matches
                if (!passwordEncoder.matches(request.getPassword(), user.getPassword())) {
                        throw new ResponseStatusException(
                                        HttpStatus.UNAUTHORIZED, "Invalid credentials");
                }

                // Check if account is enabled
                if (!user.isEnabled()) {
                        throw new ResponseStatusException(
                                        HttpStatus.FORBIDDEN, "Account disabled");
                }

                // Generate JWT token for authenticated user
                String token = jwtService.generateToken(user.getEmail());
                log.info("User logged in: {}", user.getEmail());

                return AuthResponse.builder()
                                .token(token)
                                .email(user.getEmail())
                                .build();
        }
}
