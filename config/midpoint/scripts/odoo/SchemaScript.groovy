import org.identityconnectors.framework.common.objects.ObjectClass
import org.identityconnectors.framework.common.objects.AttributeInfo
import org.identityconnectors.framework.common.objects.AttributeInfoBuilder

// Définition du schéma pour les utilisateurs Odoo
def builder = new org.identityconnectors.framework.common.objects.SchemaBuilder()

// Classe d'objet : Account
def accountObjClass = new org.identityconnectors.framework.common.objects.ObjectClassInfoBuilder()
accountObjClass.setType(ObjectClass.ACCOUNT_NAME)

// __UID__ : ID de l'utilisateur Odoo (lecture seule)
def uidBuilder = new AttributeInfoBuilder("__UID__")
uidBuilder.setRequired(false)
uidBuilder.setCreateable(false)
uidBuilder.setUpdateable(false)
uidBuilder.setReadable(true)
accountObjClass.addAttributeInfo(uidBuilder.build())

// __NAME__ : login de l'utilisateur (identifiant unique)
def nameBuilder = new AttributeInfoBuilder("__NAME__")
nameBuilder.setRequired(true)
nameBuilder.setCreateable(true)
nameBuilder.setUpdateable(false) // Le login ne peut pas être modifié
nameBuilder.setReadable(true)
accountObjClass.addAttributeInfo(nameBuilder.build())

// name : Nom complet de l'utilisateur
def fullNameBuilder = new AttributeInfoBuilder("name")
fullNameBuilder.setRequired(true)
fullNameBuilder.setCreateable(true)
fullNameBuilder.setUpdateable(true)
fullNameBuilder.setReadable(true)
accountObjClass.addAttributeInfo(fullNameBuilder.build())

// email : Email de l'utilisateur
def emailBuilder = new AttributeInfoBuilder("email")
emailBuilder.setRequired(true)
emailBuilder.setCreateable(true)
emailBuilder.setUpdateable(true)
emailBuilder.setReadable(true)
accountObjClass.addAttributeInfo(emailBuilder.build())

// active : Statut actif/inactif
def activeBuilder = new AttributeInfoBuilder("active")
activeBuilder.setType(Boolean.class)
activeBuilder.setRequired(false)
activeBuilder.setCreateable(true)
activeBuilder.setUpdateable(true)
activeBuilder.setReadable(true)
accountObjClass.addAttributeInfo(activeBuilder.build())

// groups_id : Liste des groupes (multi-valué)
def groupsBuilder = new AttributeInfoBuilder("groups_id")
groupsBuilder.setMultiValued(true)
groupsBuilder.setRequired(false)
groupsBuilder.setCreateable(true)
groupsBuilder.setUpdateable(true)
groupsBuilder.setReadable(true)
accountObjClass.addAttributeInfo(groupsBuilder.build())

// partner_id : ID du partner associé (lecture seule)
def partnerBuilder = new AttributeInfoBuilder("partner_id")
partnerBuilder.setRequired(false)
partnerBuilder.setCreateable(false)
partnerBuilder.setUpdateable(false)
partnerBuilder.setReadable(true)
accountObjClass.addAttributeInfo(partnerBuilder.build())

builder.defineObjectClass(accountObjClass.build())

log.info("Schema defined for Odoo users")
return builder.build()
