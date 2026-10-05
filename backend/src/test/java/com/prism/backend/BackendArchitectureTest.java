package com.prism.backend;

import com.tngtech.archunit.core.domain.JavaClasses;
import com.tngtech.archunit.core.importer.ClassFileImporter;
import com.tngtech.archunit.lang.ArchRule;
import org.junit.jupiter.api.Test;

import static com.tngtech.archunit.lang.syntax.ArchRuleDefinition.classes;
import static com.tngtech.archunit.lang.syntax.ArchRuleDefinition.noClasses;

class BackendArchitectureTest {

    private static final JavaClasses BACKEND_CLASSES =
            new ClassFileImporter().importPackages("com.prism.backend");

    @Test
    void backend_classes_must_remain_inside_backend_namespace() {
        ArchRule rule = classes()
                .should()
                .resideInAnyPackage(
                        "com.prism.backend.."
                );

        rule.check(BACKEND_CLASSES);
    }

    @Test
    void controllers_must_not_depend_on_repositories() {
        ArchRule rule = noClasses()
                .that()
                .resideInAPackage("com.prism.backend.controller..")
                .should()
                .dependOnClassesThat()
                .resideInAnyPackage("com.prism.backend.repository..");

        rule.check(BACKEND_CLASSES);
    }

    @Test
    void controllers_must_not_depend_on_external_integration_adapters() {
        ArchRule rule = noClasses()
                .that()
                .resideInAPackage("com.prism.backend.controller..")
                .should()
                .dependOnClassesThat()
                .resideInAnyPackage("com.prism.backend.integration..");

        rule.check(BACKEND_CLASSES);
    }

    @Test
    void services_must_not_depend_on_controllers() {
        ArchRule rule = noClasses()
                .that()
                .resideInAPackage("com.prism.backend.service..")
                .should()
                .dependOnClassesThat()
                .resideInAnyPackage("com.prism.backend.controller..");

        rule.check(BACKEND_CLASSES);
    }

    @Test
    void repository_layer_must_not_depend_on_controllers() {
        ArchRule rule = noClasses()
                .that()
                .resideInAPackage("com.prism.backend.repository..")
                .should()
                .dependOnClassesThat()
                .resideInAnyPackage("com.prism.backend.controller..");

        rule.check(BACKEND_CLASSES);
    }

    @Test
    void backend_must_not_depend_on_legacy_java_namespace() {
        ArchRule rule = noClasses()
                .should()
                .dependOnClassesThat()
                .resideInAnyPackage("com.project..");

        rule.check(BACKEND_CLASSES);
    }

    @Test
    void backend_must_not_create_cyclic_package_dependencies() {
        ArchRule rule = com.tngtech.archunit.library.dependencies.SlicesRuleDefinition
                .slices()
                .matching("com.prism.backend.(*)..")
                .should()
                .beFreeOfCycles();

        rule.check(BACKEND_CLASSES);
    }
}
