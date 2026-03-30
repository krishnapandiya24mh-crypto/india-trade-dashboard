import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from db_cloud import get_engine, q, get_stats, is_cloud
engine = get_engine()

"""
India Trade Intelligence Dashboard
7 tabs: Overview | Commodity | Country | World Map | Trends | Monthly Returns | YoY
Works on local SQLite AND Supabase cloud DB.
"""
import os,sys,glob
import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

BASE=os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0,os.path.join(BASE,"..","src"))

st.set_page_config(page_title="India Trade Intelligence",page_icon="IN",
                   layout="wide",initial_sidebar_state="expanded")
st.markdown("""<style>
.block-container{padding-top:0.8rem}
div[data-testid="metric-container"]{background:#1a1d2e;border-radius:8px;padding:10px;margin:2px}
</style>""",unsafe_allow_html=True)

ISO3={"U_S_A":"USA","USA":"USA","U_A_E":"ARE","UAE":"ARE","SAUDI_ARAB":"SAU",
      "CHINA_P":"CHN","CHINA":"CHN","NETHERLAND":"NLD","NETHERLANDS":"NLD",
      "SINGAPORE":"SGP","GERMANY":"DEU","JAPAN":"JPN","AUSTRALIA":"AUS",
      "BANGLADESH":"BGD","UK":"GBR","FRANCE":"FRA","ITALY":"ITA","BRAZIL":"BRA",
      "CANADA":"CAN","HONG_KONG":"HKG","INDONESIA":"IDN","MALAYSIA":"MYS",
      "SOUTH_AFRICA":"ZAF","BELGIUM":"BEL","IRAN":"IRN","IRAQ":"IRQ",
      "ISRAEL":"ISR","KENYA":"KEN","ETHIOPIA":"ETH","SRI_LANKA":"LKA",
      "VIETNAM":"VNM","TURKEY":"TUR","EGYPT":"EGY","EGYPT_A":"EGY",
      "RUSSIA":"RUS","SOUTH_KOREA":"KOR","THAILAND":"THA","TAIWAN":"TWN",
      "MEXICO":"MEX","SWEDEN":"SWE","SWITZERLAND":"CHE","SPAIN":"ESP",
      "SAUDI_ARABIA":"SAU","UNITED_KINGDOM":"GBR","UNITED STATES":"USA",}

from db_cloud import q,get_stats,is_cloud

@st.cache_data(ttl=600,show_spinner=False)
def cq(sql,params=()):
    return q(sql,params)

@st.cache_data(ttl=600)
def stats_cached():
    return get_stats()

@st.cache_data(ttl=600)
def hs_list():
    df=cq("SELECT DISTINCT hs_code,hs_description FROM cxc ORDER BY hs_code")
    df["label"]=df["hs_code"]+" — "+df["hs_description"].str[:55]
    return df

@st.cache_data(ttl=600)
def country_list():
    return cq("SELECT DISTINCT country FROM cxc ORDER BY country")["country"].tolist()

stats=stats_cached()
if stats["cxc_rows"]==0:
    st.title("India Trade Intelligence")
    st.error("No data. Run: python main.py --process")
    st.stop()

st.title("India Trade Intelligence")
st.caption(f"{'☁️ Cloud' if is_cloud() else '💻 Local'} | "
           f"**{stats['cxc_rows']:,} records** | **{stats['hs_codes']:,} HS4** | "
           f"**{stats['countries']:,} countries** | **{stats['date_range']}** | Ministry of Commerce")

st.sidebar.markdown("## Filters")
flow=st.sidebar.radio("Trade Flow",["Exports","Imports"],horizontal=True)
vc ="export_usd_mn" if flow=="Exports" else "import_usd_mn"
sc ="export_share_pct" if flow=="Exports" else "import_share_pct"
all_ct=country_list()
hdf=hs_list()

xl=glob.glob(os.path.join(BASE,"..","data","excel","*.xlsx"))
if xl:
    lxl=max(xl,key=os.path.getmtime)
    with open(lxl,"rb") as f:
        st.sidebar.download_button("Download Excel",f,os.path.basename(lxl),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True)
st.sidebar.markdown("---")
if st.sidebar.button("Refresh",use_container_width=True):
    st.cache_data.clear();st.rerun()

T=st.tabs(["Overview","Commodity Drill-Down","Country Analysis","World Map",
            "Trend Charts","Monthly Returns","YoY Growth"])

# ── TAB 1: OVERVIEW ───────────────────────────────────────────────────────────
with T[0]:
    ld=cq("SELECT MAX(date) FROM cxc").iloc[0,0]
    ldf=cq(f"SELECT * FROM cxc WHERE date='{ld}'")
    ldf["date"]=pd.to_datetime(ldf["date"])
    ll=pd.to_datetime(ld).strftime("%b %Y")
    te,ti=ldf["export_usd_mn"].sum(),ldf["import_usd_mn"].sum()
    c1,c2,c3,c4,c5=st.columns(5)
    c1.metric("Exports (USD Mn)",f"{te:,.0f}")
    c2.metric("Imports (USD Mn)",f"{ti:,.0f}")
    c3.metric("Balance",f"{te-ti:+,.0f}",delta="Surplus" if te>=ti else "Deficit")
    c4.metric("HS4 Codes",f"{ldf['hs_code'].nunique():,}")
    c5.metric("Countries",f"{ldf['country'].nunique():,}")
    st.markdown(f"#### Latest Month: **{ll}**")
    st.markdown("---")
    col1,col2=st.columns(2)
    with col1:
        st.markdown(f"#### Top 25 Exports — {ll}")
        te2=(ldf.groupby(["hs_code","hs_description"])["export_usd_mn"]
                .sum().reset_index().sort_values("export_usd_mn",ascending=False).head(25))
        te2["lbl"]=te2["hs_code"]+" "+te2["hs_description"].str[:28]
        fig=px.bar(te2,x="export_usd_mn",y="lbl",orientation="h",
                   color="export_usd_mn",color_continuous_scale="Blues",
                   template="plotly_dark",labels={"export_usd_mn":"USD Mn","lbl":""})
        fig.update_layout(height=550,showlegend=False,coloraxis_showscale=False,
                          yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig,use_container_width=True)
    with col2:
        st.markdown(f"#### Top 25 Imports — {ll}")
        ti2=(ldf.groupby(["hs_code","hs_description"])["import_usd_mn"]
                .sum().reset_index().sort_values("import_usd_mn",ascending=False).head(25))
        ti2["lbl"]=ti2["hs_code"]+" "+ti2["hs_description"].str[:28]
        fig2=px.bar(ti2,x="import_usd_mn",y="lbl",orientation="h",
                    color="import_usd_mn",color_continuous_scale="Reds",
                    template="plotly_dark",labels={"import_usd_mn":"USD Mn","lbl":""})
        fig2.update_layout(height=550,showlegend=False,coloraxis_showscale=False,
                           yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig2,use_container_width=True)
    st.markdown("#### Trade Balance by HS4 (Top 30)")
    bal=(ldf.groupby(["hs_code","hs_description"])
            .agg(exp=("export_usd_mn","sum"),imp=("import_usd_mn","sum")).reset_index())
    bal["balance"]=bal["exp"]-bal["imp"]
    bal["lbl"]=bal["hs_code"]+" "+bal["hs_description"].str[:30]
    bal=bal.reindex(bal["balance"].abs().sort_values(ascending=False).index).head(30)
    bal["color"]=bal["balance"].apply(lambda x:"Surplus" if x>=0 else "Deficit")
    fig3=px.bar(bal,x="lbl",y="balance",color="color",
                color_discrete_map={"Surplus":"#27AE60","Deficit":"#E74C3C"},
                template="plotly_dark",labels={"balance":"USD Mn","lbl":""})
    fig3.update_layout(height=350,xaxis_tickangle=-45)
    st.plotly_chart(fig3,use_container_width=True)

# ── TAB 2: COMMODITY DRILL-DOWN ───────────────────────────────────────────────
with T[1]:
    st.markdown("#### Commodity Drill-Down — HS4 Level")
    sel=st.selectbox("Select HS4",hdf["hs_code"].tolist(),
                     format_func=lambda x:hdf[hdf["hs_code"]==x]["label"].values[0]
                     if len(hdf[hdf["hs_code"]==x]) else x)
    hd=cq("SELECT * FROM cxc WHERE hs_code=?",(sel,))
    hd["date"]=pd.to_datetime(hd["date"])
    if hd.empty: st.info("No data.")
    else:
        desc=hd["hs_description"].iloc[0]
        st.markdown(f"**HS {sel}** — {desc}")
        c1,c2,c3,c4=st.columns(4)
        c1.metric("Total Exports",f"${hd['export_usd_mn'].sum():,.1f} Mn")
        c2.metric("Total Imports",f"${hd['import_usd_mn'].sum():,.1f} Mn")
        c3.metric("Balance",f"${hd['export_usd_mn'].sum()-hd['import_usd_mn'].sum():+,.1f} Mn")
        c4.metric("Partner Countries",hd["country"].nunique())
        lm=hd["date"].max();lhs=hd[hd["date"]==lm]
        col1,col2=st.columns(2)
        with col1:
            st.markdown(f"#### Exports — {lm.strftime('%b %Y')}")
            ex=(lhs.groupby("country")["export_usd_mn"].sum()
                   .reset_index().sort_values("export_usd_mn",ascending=False))
            ex=ex[ex["export_usd_mn"]>0]
            ex["share%"]=(ex["export_usd_mn"]/ex["export_usd_mn"].sum()*100).round(2)
            ex["cum%"]=ex["share%"].cumsum().round(2)
            ex=ex.reset_index(drop=True);ex.index=range(1,len(ex)+1)
            ex.columns=["Country","Export (USD Mn)","Share %","Cumulative %"]
            st.dataframe(ex,use_container_width=True,height=320)
            if not ex.empty:
                fig=px.pie(ex.head(15),names="Country",values="Export (USD Mn)",
                           hole=0.35,template="plotly_dark",title=f"Export Share HS {sel}")
                fig.update_layout(height=300)
                st.plotly_chart(fig,use_container_width=True)
        with col2:
            st.markdown(f"#### Imports — {lm.strftime('%b %Y')}")
            im=(lhs.groupby("country")["import_usd_mn"].sum()
                   .reset_index().sort_values("import_usd_mn",ascending=False))
            im=im[im["import_usd_mn"]>0]
            im["share%"]=(im["import_usd_mn"]/im["import_usd_mn"].sum()*100).round(2)
            im["cum%"]=im["share%"].cumsum().round(2)
            im=im.reset_index(drop=True);im.index=range(1,len(im)+1)
            im.columns=["Country","Import (USD Mn)","Share %","Cumulative %"]
            st.dataframe(im,use_container_width=True,height=320)
            if not im.empty:
                fig2=px.pie(im.head(15),names="Country",values="Import (USD Mn)",
                            hole=0.35,template="plotly_dark",
                            color_discrete_sequence=px.colors.sequential.Reds_r,
                            title=f"Import Share HS {sel}")
                fig2.update_layout(height=300)
                st.plotly_chart(fig2,use_container_width=True)
        st.markdown(f"#### Monthly Trend — HS {sel}")
        mo=(hd.groupby("date").agg(exports=("export_usd_mn","sum"),
                                    imports=("import_usd_mn","sum")).reset_index())
        fig3=go.Figure()
        fig3.add_trace(go.Scatter(x=mo["date"],y=mo["exports"],name="Exports",
                                   line=dict(color="#3498DB",width=2.5)))
        fig3.add_trace(go.Scatter(x=mo["date"],y=mo["imports"],name="Imports",
                                   line=dict(color="#E74C3C",width=2.5)))
        fig3.update_layout(template="plotly_dark",height=250,hovermode="x unified",
                           margin=dict(t=10,b=10))
        st.plotly_chart(fig3,use_container_width=True)
        am=(hd.groupby(["date","country"])
              .agg(exports=("export_usd_mn","sum"),imports=("import_usd_mn","sum"))
              .reset_index())
        am["date"]=am["date"].dt.strftime("%b-%Y")
        am["exp%"]=(am.groupby("date")["exports"].transform(lambda x:x/x.sum()*100)).round(2)
        am["imp%"]=(am.groupby("date")["imports"].transform(lambda x:x/x.sum()*100)).round(2)
        am=am.sort_values(["date","exports"],ascending=[True,False]).round(2)
        st.dataframe(am,use_container_width=True,height=320)
        st.download_button(f"Download HS {sel} CSV",am.to_csv(index=False),
                           f"HS_{sel}.csv","text/csv")

# ── TAB 3: COUNTRY ANALYSIS ───────────────────────────────────────────────────
with T[2]:
    st.markdown("#### Country Analysis")
    cs=cq("SELECT country,SUM(export_usd_mn) AS te,SUM(import_usd_mn) AS ti,"
           "COUNT(DISTINCT hs_code) AS hs,COUNT(DISTINCT date) AS mo "
           "FROM cxc GROUP BY country ORDER BY te DESC")
    cs["bal"]=cs["te"]-cs["ti"]
    cs["exp%"]=(cs["te"]/cs["te"].sum()*100).round(2)
    cs["imp%"]=(cs["ti"]/cs["ti"].sum()*100).round(2)
    srch=st.text_input("Search country","")
    disp=cs[cs["country"].str.contains(srch,case=False)] if srch else cs
    disp=disp.round(2).reset_index(drop=True);disp.index=range(1,len(disp)+1)
    disp.columns=["Country","Total Exports","Total Imports","# HS","# Months","Balance","Exp%","Imp%"]
    st.dataframe(disp,use_container_width=True,height=300)
    st.markdown("---")
    sel_ct=st.selectbox("Select Country",cs["country"].tolist())
    cd=cq("SELECT * FROM cxc WHERE country=?",(sel_ct,))
    if not cd.empty:
        cd["date"]=pd.to_datetime(cd["date"])
        lc=cd["date"].max()
        c1,c2,c3=st.columns(3)
        c1.metric("Total Exports",f"${cd['export_usd_mn'].sum():,.1f} Mn")
        c2.metric("Total Imports",f"${cd['import_usd_mn'].sum():,.1f} Mn")
        c3.metric("HS4 Commodities",cd["hs_code"].nunique())
        lcd=cd[cd["date"]==lc]
        col1,col2=st.columns(2)
        with col1:
            st.markdown(f"**Top Exports TO {sel_ct}** — {lc.strftime('%b %Y')}")
            t1=(lcd[lcd["export_usd_mn"]>0].nlargest(20,"export_usd_mn")
                [["hs_code","hs_description","export_usd_mn","export_share_pct"]]
                .round(2).reset_index(drop=True))
            t1.index=range(1,len(t1)+1);t1.columns=["HS","Desc","Export (USD Mn)","Share %"]
            st.dataframe(t1,use_container_width=True,height=380)
        with col2:
            st.markdown(f"**Top Imports FROM {sel_ct}** — {lc.strftime('%b %Y')}")
            t2=(lcd[lcd["import_usd_mn"]>0].nlargest(20,"import_usd_mn")
                [["hs_code","hs_description","import_usd_mn","import_share_pct"]]
                .round(2).reset_index(drop=True))
            t2.index=range(1,len(t2)+1);t2.columns=["HS","Desc","Import (USD Mn)","Share %"]
            st.dataframe(t2,use_container_width=True,height=380)

# ── TAB 4: WORLD MAP ──────────────────────────────────────────────────────────
with T[3]:
    st.markdown("#### World Trade Map")
    mf=st.radio("Flow",["Exports","Imports"],horizontal=True,key="mf")
    mc2="export_usd_mn" if mf=="Exports" else "import_usd_mn"
    hm=st.selectbox("Filter by HS Code",["All HS Codes"]+hdf["hs_code"].tolist(),key="hm")
    if hm=="All HS Codes":
        mdf=cq(f"SELECT country,SUM({mc2}) AS val FROM cxc GROUP BY country")
    else:
        mdf=cq(f"SELECT country,SUM({mc2}) AS val FROM cxc WHERE hs_code=? GROUP BY country",(hm,))
    mdf["iso3"]=mdf["country"].map(ISO3)
    mdf=mdf.dropna(subset=["iso3"]).round(2)
    fig=px.choropleth(mdf,locations="iso3",color="val",hover_name="country",
                      color_continuous_scale="Blues" if mf=="Exports" else "Reds",
                      template="plotly_dark",labels={"val":f"{mf} (USD Mn)"},
                      title=f"India {mf}"+(f" — HS {hm}" if hm!="All HS Codes" else ""))
    fig.update_geos(showcoastlines=True,coastlinecolor="#444",showland=True,
                    landcolor="#1a1d2e",showocean=True,oceancolor="#0d0f1a",showframe=False)
    fig.update_layout(height=460,margin=dict(l=0,r=0,t=40,b=0))
    st.plotly_chart(fig,use_container_width=True)
    tm=mdf.sort_values("val",ascending=False).head(20)
    tm["share%"]=(tm["val"]/tm["val"].sum()*100).round(2)
    tm=tm[["country","val","share%"]].reset_index(drop=True)
    tm.index=range(1,len(tm)+1);tm.columns=["Country",f"{mf} (USD Mn)","Share %"]
    st.dataframe(tm,use_container_width=True)

# ── TAB 5: TREND CHARTS ───────────────────────────────────────────────────────
with T[4]:
    st.markdown("#### Monthly Trend Charts")
    c1,c2=st.columns(2)
    with c1: tb=st.radio("View by",["HS4","Country"],horizontal=True)
    with c2: tn=st.slider("Top N",3,15,8)
    if tb=="HS4":
        toph=cq(f"SELECT hs_code,hs_description,SUM(export_usd_mn) AS tot FROM cxc GROUP BY hs_code ORDER BY tot DESC LIMIT {tn}")
        hl=toph["hs_code"].tolist()
        tdf=cq(f"SELECT date,hs_code,hs_description,SUM(export_usd_mn) AS exports,SUM(import_usd_mn) AS imports FROM cxc WHERE hs_code IN ({','.join('?'*len(hl))}) GROUP BY date,hs_code ORDER BY date",tuple(hl))
        tdf["date"]=pd.to_datetime(tdf["date"])
        tdf["label"]=tdf["hs_code"]+" "+tdf["hs_description"].str[:18]
        cv="exports" if flow=="Exports" else "imports"
        fig=px.line(tdf,x="date",y=cv,color="label",title=f"Monthly {flow} — Top {tn} HS4",
                    template="plotly_dark",labels={cv:"USD Mn","date":"","label":"HS"})
        fig.update_layout(height=380,hovermode="x unified",
                          legend=dict(orientation="h",yanchor="bottom",y=1.02))
        st.plotly_chart(fig,use_container_width=True)
    else:
        topc=cq(f"SELECT country,SUM(export_usd_mn) AS tot FROM cxc GROUP BY country ORDER BY tot DESC LIMIT {tn}")
        cl=topc["country"].tolist()
        tdf=cq(f"SELECT date,country,SUM(export_usd_mn) AS exports,SUM(import_usd_mn) AS imports FROM cxc WHERE country IN ({','.join('?'*len(cl))}) GROUP BY date,country ORDER BY date",tuple(cl))
        tdf["date"]=pd.to_datetime(tdf["date"])
        cv="exports" if flow=="Exports" else "imports"
        fig=px.line(tdf,x="date",y=cv,color="country",title=f"Monthly {flow} — Top {tn} Countries",
                    template="plotly_dark",labels={cv:"USD Mn","date":""})
        fig.update_layout(height=380,hovermode="x unified",
                          legend=dict(orientation="h",yanchor="bottom",y=1.02))
        st.plotly_chart(fig,use_container_width=True)
    st.markdown("#### India Monthly Trade Balance")
    bl=cq("SELECT date,SUM(export_usd_mn) AS e,SUM(import_usd_mn) AS m FROM cxc GROUP BY date ORDER BY date")
    bl["date"]=pd.to_datetime(bl["date"]);bl["balance"]=bl["e"]-bl["m"]
    bl["color"]=bl["balance"].apply(lambda x:"#27AE60" if x>=0 else "#E74C3C")
    fig2=go.Figure()
    fig2.add_trace(go.Bar(x=bl["date"],y=bl["balance"],marker_color=bl["color"],name="Balance",opacity=0.8))
    fig2.add_trace(go.Scatter(x=bl["date"],y=bl["e"],name="Exports",line=dict(color="#3498DB",width=2)))
    fig2.add_trace(go.Scatter(x=bl["date"],y=bl["m"],name="Imports",line=dict(color="#E74C3C",width=2)))
    fig2.update_layout(template="plotly_dark",height=290,hovermode="x unified",
                       legend=dict(orientation="h",yanchor="bottom",y=1.02))
    st.plotly_chart(fig2,use_container_width=True)

# ── TAB 6: MONTHLY RETURNS ────────────────────────────────────────────────────
with T[5]:
    st.markdown("#### Monthly Returns — MoM % Change in Trade Value")
    st.caption("Like stock returns but for trade flows. Green = growth, Red = decline.")
    mr=st.radio("Calculate for",["Overall India","By HS4 Commodity","By Country"],horizontal=True)

    if mr=="Overall India":
        ov=cq("SELECT date,SUM(export_usd_mn) AS e,SUM(import_usd_mn) AS m FROM cxc GROUP BY date ORDER BY date")
        ov["date"]=pd.to_datetime(ov["date"])
        ov["exp_ret%"]=ov["e"].pct_change()*100
        ov["imp_ret%"]=ov["m"].pct_change()*100
        ov["balance"]=ov["e"]-ov["m"]
        ov["bal_chg"]=ov["balance"].diff()
        ov["month"]=ov["date"].dt.strftime("%b-%Y")
        vd=ov.dropna(subset=["exp_ret%"])
        c1,c2,c3,c4=st.columns(4)
        c1.metric("Avg Export MoM",f"{ov['exp_ret%'].mean():.1f}%")
        c2.metric("Avg Import MoM",f"{ov['imp_ret%'].mean():.1f}%")
        if not vd.empty:
            c3.metric("Best Export Month",vd.loc[vd['exp_ret%'].idxmax(),'month'])
            c4.metric("Worst Export Month",vd.loc[vd['exp_ret%'].idxmin(),'month'])
        fig=make_subplots(rows=2,cols=1,subplot_titles=("Export MoM Return %","Import MoM Return %"),
                          row_heights=[0.5,0.5],vertical_spacing=0.12)
        ec=["#27AE60" if x>=0 else "#E74C3C" for x in ov["exp_ret%"].fillna(0)]
        ic=["#27AE60" if x>=0 else "#E74C3C" for x in ov["imp_ret%"].fillna(0)]
        fig.add_trace(go.Bar(x=ov["date"],y=ov["exp_ret%"],marker_color=ec,name="Export"),row=1,col=1)
        fig.add_trace(go.Bar(x=ov["date"],y=ov["imp_ret%"],marker_color=ic,name="Import"),row=2,col=1)
        fig.add_hline(y=0,line_dash="dash",line_color="white",opacity=0.3,row=1,col=1)
        fig.add_hline(y=0,line_dash="dash",line_color="white",opacity=0.3,row=2,col=1)
        fig.update_layout(template="plotly_dark",height=400,showlegend=False,hovermode="x unified")
        st.plotly_chart(fig,use_container_width=True)
        tbl=ov[["month","e","exp_ret%","m","imp_ret%","balance","bal_chg"]].dropna().round(2)
        tbl.columns=["Month","Exports","Export MoM %","Imports","Import MoM %","Balance","Balance Chg"]
        tbl.index=range(1,len(tbl)+1)
        st.dataframe(tbl,use_container_width=True,height=380)
        st.download_button("Download CSV",tbl.to_csv(index=False),"monthly_returns.csv","text/csv")

    elif mr=="By HS4 Commodity":
        srh=st.selectbox("Select HS4",hdf["hs_code"].tolist(),key="mrhs",
                         format_func=lambda x:hdf[hdf["hs_code"]==x]["label"].values[0]
                         if len(hdf[hdf["hs_code"]==x]) else x)
        hr=cq("SELECT date,SUM(export_usd_mn) AS e,SUM(import_usd_mn) AS m FROM cxc WHERE hs_code=? GROUP BY date ORDER BY date",(srh,))
        hr["date"]=pd.to_datetime(hr["date"])
        hr["exp_ret%"]=hr["e"].pct_change()*100
        hr["imp_ret%"]=hr["m"].pct_change()*100
        hr["month"]=hr["date"].dt.strftime("%b-%Y")
        if len(hr)>1:
            c1,c2=st.columns(2)
            c1.metric("Avg Export MoM",f"{hr['exp_ret%'].mean():.1f}%")
            c2.metric("Avg Import MoM",f"{hr['imp_ret%'].mean():.1f}%")
            fig=make_subplots(rows=2,cols=1,
                              subplot_titles=(f"HS {srh} Export MoM %",f"HS {srh} Import MoM %"),
                              row_heights=[0.5,0.5],vertical_spacing=0.12)
            ec=["#27AE60" if x>=0 else "#E74C3C" for x in hr["exp_ret%"].fillna(0)]
            ic=["#27AE60" if x>=0 else "#E74C3C" for x in hr["imp_ret%"].fillna(0)]
            fig.add_trace(go.Bar(x=hr["date"],y=hr["exp_ret%"],marker_color=ec),row=1,col=1)
            fig.add_trace(go.Bar(x=hr["date"],y=hr["imp_ret%"],marker_color=ic),row=2,col=1)
            fig.add_hline(y=0,line_dash="dash",line_color="white",opacity=0.3,row=1,col=1)
            fig.add_hline(y=0,line_dash="dash",line_color="white",opacity=0.3,row=2,col=1)
            fig.update_layout(template="plotly_dark",height=400,showlegend=False)
            st.plotly_chart(fig,use_container_width=True)
            tbl=hr[["month","e","exp_ret%","m","imp_ret%"]].dropna().round(2)
            tbl.columns=["Month","Exports","Export MoM %","Imports","Import MoM %"]
            tbl.index=range(1,len(tbl)+1)
            st.dataframe(tbl,use_container_width=True)
            st.download_button(f"Download HS {srh}",tbl.to_csv(index=False),f"ret_HS_{srh}.csv","text/csv")

    else:
        src=st.selectbox("Select Country",all_ct,key="mrct")
        cr=cq("SELECT date,SUM(export_usd_mn) AS e,SUM(import_usd_mn) AS m FROM cxc WHERE country=? GROUP BY date ORDER BY date",(src,))
        cr["date"]=pd.to_datetime(cr["date"])
        cr["exp_ret%"]=cr["e"].pct_change()*100
        cr["imp_ret%"]=cr["m"].pct_change()*100
        cr["month"]=cr["date"].dt.strftime("%b-%Y")
        if len(cr)>1:
            c1,c2=st.columns(2)
            c1.metric("Avg Export MoM",f"{cr['exp_ret%'].mean():.1f}%")
            c2.metric("Avg Import MoM",f"{cr['imp_ret%'].mean():.1f}%")
            fig=make_subplots(rows=2,cols=1,
                              subplot_titles=(f"{src} Export MoM %",f"{src} Import MoM %"),
                              row_heights=[0.5,0.5],vertical_spacing=0.12)
            ec=["#27AE60" if x>=0 else "#E74C3C" for x in cr["exp_ret%"].fillna(0)]
            ic=["#27AE60" if x>=0 else "#E74C3C" for x in cr["imp_ret%"].fillna(0)]
            fig.add_trace(go.Bar(x=cr["date"],y=cr["exp_ret%"],marker_color=ec),row=1,col=1)
            fig.add_trace(go.Bar(x=cr["date"],y=cr["imp_ret%"],marker_color=ic),row=2,col=1)
            fig.add_hline(y=0,line_dash="dash",line_color="white",opacity=0.3,row=1,col=1)
            fig.add_hline(y=0,line_dash="dash",line_color="white",opacity=0.3,row=2,col=1)
            fig.update_layout(template="plotly_dark",height=400,showlegend=False)
            st.plotly_chart(fig,use_container_width=True)
            tbl=cr[["month","e","exp_ret%","m","imp_ret%"]].dropna().round(2)
            tbl.columns=["Month","Exports","Export MoM %","Imports","Import MoM %"]
            tbl.index=range(1,len(tbl)+1)
            st.dataframe(tbl,use_container_width=True)
            st.download_button(f"Download {src}",tbl.to_csv(index=False),f"ret_{src}.csv","text/csv")

    st.markdown("---")
    st.markdown("#### Return Heatmap — Top 20 Commodities")
    st.caption("Green = growth month, Red = decline month")
    t20=cq("SELECT hs_code,hs_description,SUM(export_usd_mn) AS tot FROM cxc GROUP BY hs_code ORDER BY tot DESC LIMIT 20")
    hf=cq(f"SELECT date,hs_code,SUM(export_usd_mn) AS e FROM cxc WHERE hs_code IN ({','.join('?'*len(t20))}) GROUP BY date,hs_code ORDER BY date",tuple(t20["hs_code"].tolist()))
    if not hf.empty:
        hf["date"]=pd.to_datetime(hf["date"])
        pv=hf.pivot(index="hs_code",columns="date",values="e")
        rp=pv.pct_change(axis=1)*100
        rp.index=[t20[t20["hs_code"]==h]["hs_description"].values[0][:28]
                  if len(t20[t20["hs_code"]==h]) else h for h in rp.index]
        rp.columns=[pd.to_datetime(c).strftime("%b-%y") for c in rp.columns]
        rp=rp.iloc[:,1:]
        fh=px.imshow(rp,color_continuous_scale="RdYlGn",color_continuous_midpoint=0,
                     zmin=-50,zmax=50,template="plotly_dark",aspect="auto",
                     title="Export MoM Return % — Top 20 Commodities",
                     labels=dict(color="MoM %"))
        fh.update_layout(height=480)
        st.plotly_chart(fh,use_container_width=True)

# ── TAB 7: YoY GROWTH ─────────────────────────────────────────────────────────
with T[6]:
    st.markdown("#### Year-on-Year Growth")
    yrs=cq("SELECT DISTINCT year FROM cxc ORDER BY year")["year"].tolist()
    if len(yrs)>=2:
        c1,c2=st.columns(2)
        cy=c1.selectbox("Current Year",sorted(yrs,reverse=True),index=0)
        py=c2.selectbox("Previous Year",sorted(yrs,reverse=True),index=1)
        cur=cq("SELECT hs_code,hs_description,SUM(export_usd_mn) AS ec,SUM(import_usd_mn) AS ic FROM cxc WHERE year=? GROUP BY hs_code",(cy,))
        prv=cq("SELECT hs_code,SUM(export_usd_mn) AS ep,SUM(import_usd_mn) AS ip FROM cxc WHERE year=? GROUP BY hs_code",(py,))
        mg=pd.merge(cur,prv,on="hs_code",how="inner")
        mg["exp_yoy%"]=((mg["ec"]-mg["ep"])/mg["ep"].replace(0,np.nan)*100).round(1)
        mg["imp_yoy%"]=((mg["ic"]-mg["ip"])/mg["ip"].replace(0,np.nan)*100).round(1)
        mg=mg.dropna(subset=["exp_yoy%","imp_yoy%"],how="all")
        col1,col2=st.columns(2)
        with col1:
            st.markdown(f"#### Top Gainers ({py}→{cy})")
            g=(mg[mg["exp_yoy%"]>0].nlargest(20,"exp_yoy%")
               [["hs_code","hs_description","ec","exp_yoy%"]].round(1))
            g.index=range(1,len(g)+1);g.columns=["HS","Desc",f"Exp {cy}","YoY %"]
            st.dataframe(g,use_container_width=True,height=420)
        with col2:
            st.markdown(f"#### Top Decliners ({py}→{cy})")
            l=(mg[mg["exp_yoy%"]<0].nsmallest(20,"exp_yoy%")
               [["hs_code","hs_description","ec","exp_yoy%"]].round(1))
            l.index=range(1,len(l)+1);l.columns=["HS","Desc",f"Exp {cy}","YoY %"]
            st.dataframe(l,use_container_width=True,height=420)
        full=mg[["hs_code","hs_description","ec","exp_yoy%","ic","imp_yoy%"]]\
             .sort_values("exp_yoy%",ascending=False).round(1)
        full.index=range(1,len(full)+1)
        full.columns=["HS","Desc",f"Exp {cy}","Exp YoY %",f"Imp {cy}","Imp YoY %"]
        st.dataframe(full,use_container_width=True,height=420)
        st.download_button("Download YoY CSV",full.to_csv(index=False),f"yoy_{cy}.csv","text/csv")
    else:
        st.info("Need at least 2 years of data.")
