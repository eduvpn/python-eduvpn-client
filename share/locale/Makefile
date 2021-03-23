
NAME     := eduVPN

POT      := $(NAME).pot
LANGS    := $(wildcard *_*)
UI_FILES := $(wildcard ../eduvpn/builder/*.ui) $(wildcard ../../eduvpn/*.py) $(wildcard ../../eduvpn/ui/*.py)
PO_FILES := $(foreach lang,$(LANGS),$(lang)/LC_MESSAGES/$(NAME).po)
MO_FILES  = $(PO_FILES:.po=.mo)

SHELL    := bash

.SUFFIXES: .ui .py .pot .mo .po
.PRECIOUS: $(PO_FILES)

default: $(POT) $(MO_FILES)

# Update pot if ui changed
$(POT): $(UI_FILES)
	xgettext --keyword=translatable --add-comments --sort-output -o $@ $^

# Create or update po if pot changed
%.po: $(POT)
	if test -a $@ ; then \
	  msgmerge --update $@ $(POT); \
	  touch $@; \
	else \
	  mkdir -p $(dir $@); \
	  msginit --input=$(POT) --locale=$(filter $(LANGS),$(subst /, ,$@)) --output=$@; \
	fi

# Update mo if po changed
%.mo: %.po
	msgfmt -v --output-file=$@ $<

