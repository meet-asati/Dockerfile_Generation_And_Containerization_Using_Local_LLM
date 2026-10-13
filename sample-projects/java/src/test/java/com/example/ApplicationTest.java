package com.example;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertTrue;

class ApplicationTest {
    @Test
    void projectHasAnApplicationEntryPoint() {
        assertTrue(Application.class.isAssignableFrom(Application.class));
    }
}
