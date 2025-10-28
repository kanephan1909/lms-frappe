import { createResource } from 'frappe-ui'
import { ref } from 'vue'

// Make translations reactive so UI updates when they arrive
const translatedMessagesRef = ref({})

export default function translationPlugin(app) {
    app.config.globalProperties.__ = translate
    window.__ = translate
    // expose for debugging
    window.__messages__ = translatedMessagesRef
    if (!Object.keys(translatedMessagesRef.value).length) fetchTranslations()
}

function translate(message) {
    // Accessing the ref here makes templates reactive to changes
    const translatedMessage = translatedMessagesRef.value[message] || message

	const hasPlaceholders = /{\d+}/.test(message)
	if (!hasPlaceholders) {
		return translatedMessage
	}
    return {
		format: function (...args) {
			return translatedMessage.replace(
				/{(\d+)}/g,
				function (match, number) {
					return typeof args[number] != 'undefined'
						? args[number]
						: match
				}
			)
		},
	}
}

function fetchTranslations(lang) {
    createResource({
		url: 'lms.lms.api.get_translations',
		cache: 'translations',
		auto: true,
		transform: (data) => {
            translatedMessagesRef.value = data || {}
            // fire a custom event in case any non-reactive consumers want to listen
            window.dispatchEvent(new CustomEvent('translations-updated'))
		},
	})
}
