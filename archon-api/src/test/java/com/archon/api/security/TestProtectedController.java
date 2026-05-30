package com.archon.api.security;

import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * Test-only protected endpoint used to validate security filter behavior.
 */
@RestController
@RequestMapping("/api/v1/protected")
public class TestProtectedController {

    @GetMapping("/me")
    public String me(Authentication authentication) {
        return String.valueOf(authentication.getPrincipal());
    }
}
