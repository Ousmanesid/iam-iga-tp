// Chargement du helper
evaluate(new File(scriptPath + '/OdooHelper.groovy'))

log.info("Deleting Odoo user ID: {0}", uid.uidValue)

try {
    def odoo = new OdooHelper(
        configuration.serviceAddress,
        configuration.username,
        configuration.password.toString()
    )
    
    def userId = uid.uidValue as Integer
    
    // Ne pas supprimer réellement, juste désactiver
    odoo.write('res.users', [userId], [active: false])
    
    log.info("✓ User deactivated successfully")
    
} catch (Exception e) {
    log.error("✗ Failed to delete user: {0}", e.message)
    throw e
}
