import org.identityconnectors.framework.common.objects.ObjectClass
import org.identityconnectors.framework.common.objects.OperationOptions

// Chargement du helper
evaluate(new File(scriptPath + '/OdooHelper.groovy'))

// Test de connexion
log.info("Testing Odoo connection...")

try {
    def odoo = new OdooHelper(
        configuration.serviceAddress,
        configuration.username,
        configuration.password.toString()
    )
    
    log.info("✓ Connection successful, UID: {0}", odoo.uid)
    
} catch (Exception e) {
    log.error("✗ Connection failed: {0}", e.message)
    throw e
}
