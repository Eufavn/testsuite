TOP=../../..
include $(TOP)/mk/boilerplate.mk
include $(TOP)/mk/test.mk

NewTyCo:
	$(RM) NewTyCo1.o NewTyCo1.hi NewTyCo2.o NewTyCo2.hi
	'$(TEST_HC)' $(TEST_HC_OPTS) -c NewTyCo1.hs
	'$(TEST_HC)' $(TEST_HC_OPTS) -c NewTyCo2.hs

.PHONY: IndTypesPerf
IndTypesPerf:
	$(RM) IndTypesPerf.o IndTypesPerf.hi
	$(RM) IndTypesPerfMerge.o IndTypesPerfMerge.hi
	'$(TEST_HC)' $(TEST_HC_OPTS) -O -c IndTypesPerfMerge.hs +RTS -M20M
	'$(TEST_HC)' $(TEST_HC_OPTS) -O -c IndTypesPerf.hs      +RTS -M20M

T5955:
	$(RM) T5955.o T5955.hi T5955a.o T5955a.hi 
	'$(TEST_HC)' $(TEST_HC_OPTS) -c T5955a.hs
	'$(TEST_HC)' $(TEST_HC_OPTS) -c T5955.hs
