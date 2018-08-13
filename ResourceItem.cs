// Decompiled with JetBrains decompiler
// Type: ResourceItem
// Assembly: Assembly-CSharp, Version=0.0.0.0, Culture=neutral, PublicKeyToken=null
// MVID: 9389A4AF-DACD-4250-864C-FFB1C86AE6D0
// Assembly location: SteamLibrary\steamapps\common\Blockhood\BLOCKHOOD v0_40_08_Data\Managed\Assembly-CSharp.dll

using System;
using UnityEngine;

[Serializable]
public class ResourceItem
{
  #region Members

  public Sprite icon;
  public string myName;
  public float cost;
  private Manager myManager;
  public string alias;
  public string description;
  public string alias_spanish;
  public string description_spanish;
  public string alias_japanese;
  public string description_japanese;
  public string alias_french;
  public string description_french;
  public string alias_german;
  public string description_german;
  public string alias_italian;
  public string description_italian;
  public string alias_portugese;
  public string description_portugese;
  public string alias_korean;
  public string description_korean;
  public string alias_chinese;
  public string description_chinese;
  public string alias_russian;
  public string description_russian;
  public string alias_hungarian;
  public string description_hungarian;
  public int levelOfFinish;
  public ResourceItem.Category category;
  public ResourceItem.Tags tag;
  public ResourceItem.Units myUnits;

  #endregion
	
  public enum Category
  {
    EMPTY,
    FOOD,
    ENERGY,
    JOB,
    SERVICE,
    ORGANIC,
    INORGANIC,
  }

  public enum Tags
  {
    EMPTY,
    GRAIN,
    VEGETABLE,
    FRUIT,
    ENERGY,
    LABOR,
    MEAT,
    COMODITY,
    WASTE,
    RAW_MATERIALS,
    DAIRY,
    CONSUMABLE,
    ORGANIC,
    INORGANIC,
    COMMUNITY,
  }

  public enum Units
  {
    kg,
    mg,
    lt,
    tons,
    amps,
    volt,
    joule,
    cal,
    pts,
  }
}
