module TH_spliceDecl3_Lib
where

import Language.Haskell.THSyntax

rename' :: Dec -> Q [Dec]
rename' (DataD ctxt tyName tyvars cons derivs) =
  return [DataD ctxt (stripMod tyName ++ "'") tyvars (map renameCons cons) derivs]
  where
    renameCons (NormalC conName tys) = NormalC (stripMod conName ++ "'") tys
    --
    stripMod = tail . snd . break (== ':')
