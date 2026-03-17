.PHONY: dev build

# Run the local development server
dev:
	hugo server -D -F -e development -b http://localhost:1313/ --disableFastRender --navigateToChanged --noHTTPCache --gc --printI18nWarnings --printPathWarnings --printUnusedTemplates

# Build the site for production
build:
	hugo --gc --minify
