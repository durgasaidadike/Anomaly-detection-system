package com.prism.backend.controller;

import jakarta.validation.constraints.NotBlank;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;

class ValidationAdviceTest {

    record TestRequest(
            @NotBlank String requiredField
    ) {}

    @Test
    void validationAdviceIsPresent() {
        ValidationAdvice advice = new ValidationAdvice();
        assertNotNull(advice);
    }

    @Test
    void validationRejectsBlankField() {
        TestRequest request = new TestRequest("");

        jakarta.validation.Validator validator =
                jakarta.validation.Validation.buildDefaultValidatorFactory().getValidator();

        var violations = validator.validate(request);

        assertEquals(1, violations.size());
    }
}
