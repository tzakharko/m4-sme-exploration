# Define variables for project paths and scheme
APP_NAME  = SMETest
APP_PATH  = ./build/Release-iphoneos/$(APP_NAME).app
APP_ID    = com.tzakharko.SMETest
DEVICE_PATH = Documents/SMETest

COPY = xcrun devicectl device copy from --domain-type appDataContainer --domain-identifier "$(APP_ID)" --device "$(DEVICE)"
BENCHMARKS = src/benchmarks/op_benchmarks.c src/benchmarks/mem_benchmarks.c

ifeq (,$(wildcard ./make.config))
$(error Unable to locate make.config, did you run ./setup before make?)
endif
include make.config

# Check that the variables are set
ifndef XCODE_DEVELOPMENT_TEAM
$(error XCODE_DEVELOPMENT_TEAM is not set, did you run ./setup before make?)
endif

ifndef DEVICE
$(error DEVICE is not set, did you run ./setup before make?)
endif

# rules for generating benchmarks
benchmarks: $(BENCHMARKS)

src/benchmarks/%.c: tools/gen_%.py tools/SME.py benchmarks.yaml
	@echo "\033[0;32m-- Generating $(@)\033[0m"
	@python3 $(<) > $(@)

.PHONY: build
build: benchmarks
	@echo "\033[0;32m-- Building the app\033[0m"
	xcodegen generate
	xcodebuild clean build -configuration Release -allowProvisioningUpdates DEVELOPMENT_TEAM="$(XCODE_DEVELOPMENT_TEAM)"
	@echo "\033[0;32m-- Installing the app to $(DEVICE)\033[0m"
	xcrun devicectl device install app --device "$(DEVICE)"  "$(APP_PATH)"

.PHONY: run
run:
	@echo "\033[0;36mMake sure that $(DEVICE) is unlocked\033[0m"
	@xcrun devicectl device process launch  --console --device -j log.json "$(DEVICE)" "$(APP_ID)" # | python3 -m json.tool > results.json

.PHONY: copy_results
copy_results:
	@echo "\033[0;32mRetrieving JSON reports\033[0m"
	@$(COPY) --source "$(DEVICE_PATH)/cpu_info.json" --destination "results/cpu_info.json"
	@$(COPY) --source "$(DEVICE_PATH)/op_benchmarks.json" --destination "results/op_benchmarks.json"
	@$(COPY) --source "$(DEVICE_PATH)/mem_benchmarks.json" --destination "results/mem_benchmarks.json"


.PHONY: reports
reports:
	@quarto render reports/rmarkdown/02-sme-outer-product.qmd --to gfm --no-cache
	@mv reports/rmarkdown/*.md reports/
	@mv reports/rmarkdown/figures/*.png reports/figures
	@rm -r reports/rmarkdown/figures
