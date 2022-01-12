package com.osfans.mcpdict;

import android.content.SharedPreferences;
import android.content.res.Resources;
import android.database.Cursor;
import android.os.AsyncTask;
import android.os.Bundle;
import android.preference.PreferenceManager;
import android.text.TextUtils;
import android.text.method.LinkMovementMethod;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.AdapterView;
import android.widget.AdapterView.OnItemSelectedListener;
import android.widget.ArrayAdapter;
import android.widget.CheckBox;
import android.widget.CompoundButton;
import android.widget.Spinner;
import android.widget.TextView;

import androidx.annotation.NonNull;
import androidx.fragment.app.Fragment;

import java.util.HashMap;
import java.util.Map;
import java.util.Set;

public class DictionaryFragment extends Fragment implements RefreshableFragment {

    private View selfView;
    private CustomSearchView searchView;
    private Spinner spinnerSearchAs, spinnerShowLang;
    private CheckBox checkBoxAllowVariants;
    private SearchResultFragment fragmentResult;
    ArrayAdapter<CharSequence> adapter, adapterShowLang, adapterShowChar;

    private void updateCurrentLanguage() {
        Object column = spinnerSearchAs.getSelectedItem();
        if (column != null) Utils.putLanguage(getContext(), column.toString());
        int position = spinnerShowLang.getSelectedItemPosition();
        SharedPreferences sp = PreferenceManager.getDefaultSharedPreferences(getActivity());
        sp.edit().putInt(getString(R.string.pref_key_show_language_index), position).apply();
        String name = getResources().getStringArray(R.array.pref_values_show_languages)[position];
        if (position == 1) {
            int mode = MCPDatabase.getColumnIndex(getContext());
            name = MCPDatabase.getColumnName(mode);
            if (name.contentEquals("ja_tou")) name = "ja_.+";
        }
        sp.edit().putString(getString(R.string.pref_key_show_language_names), name).apply();
    }

    @Override
    public View onCreateView(@NonNull LayoutInflater inflater, ViewGroup container, Bundle savedInstanceState) {
        // A hack to avoid nested fragments from being inflated twice
        // Reference: http://stackoverflow.com/a/14695397
        if (selfView != null) {
            ViewGroup parent = (ViewGroup) selfView.getParent();
            if (parent != null) parent.removeView(selfView);
            return selfView;
        }

        // Inflate the fragment view
        selfView = inflater.inflate(R.layout.dictionary_fragment, container, false);

        // Set up the search view
        searchView = selfView.findViewById(R.id.search_view);
        searchView.setSearchButtonOnClickListener(view -> {
            updateCurrentLanguage();
            refresh();
            fragmentResult.scrollToTop();
        });

        // Set up the spinner
        spinnerShowLang = selfView.findViewById(R.id.spinner_show_languages);
        adapterShowLang = ArrayAdapter.createFromResource(requireActivity(),
                R.array.pref_entries_show_languages, android.R.layout.simple_spinner_item);
        adapterShowLang.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
        spinnerShowLang.setAdapter(adapterShowLang);
        int position = PreferenceManager.getDefaultSharedPreferences(getActivity()).getInt(getString(R.string.pref_key_show_language_index), 0);
        spinnerShowLang.setSelection(position);
        spinnerShowLang.setOnItemSelectedListener(new OnItemSelectedListener() {
            @Override
            public void onItemSelected(AdapterView<?> parent, View view, int position, long id) {
                searchView.clickSearchButton();
            }
            @Override
            public void onNothingSelected(AdapterView<?> parent) {}
        });

        Spinner spinnerShowChar = selfView.findViewById(R.id.spinner_show_characters);
        adapterShowChar = ArrayAdapter.createFromResource(requireActivity(),
                R.array.pref_entries_charset, android.R.layout.simple_spinner_item);
        adapterShowChar.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
        spinnerShowChar.setAdapter(adapterShowChar);
        position = PreferenceManager.getDefaultSharedPreferences(getActivity()).getInt(getString(R.string.pref_key_charset), 0);
        spinnerShowChar.setSelection(position);
        spinnerShowChar.setOnItemSelectedListener(new OnItemSelectedListener() {
            @Override
            public void onItemSelected(AdapterView<?> parent, View view, int position, long id) {
                SharedPreferences sp = PreferenceManager.getDefaultSharedPreferences(getActivity());
                sp.edit().putInt(getString(R.string.pref_key_charset), position).apply();
                searchView.clickSearchButton();
            }
            @Override
            public void onNothingSelected(AdapterView<?> parent) {}
        });

        spinnerSearchAs = selfView.findViewById(R.id.spinner_search_as);
        adapter = new ArrayAdapter<>(requireActivity(), android.R.layout.simple_spinner_item);
        refreshAdapter();
        adapter.setDropDownViewResource(R.layout.custom_spinner_dropdown_item);
        spinnerSearchAs.setAdapter(adapter);
        spinnerSearchAs.setOnItemSelectedListener(new OnItemSelectedListener() {
            @Override
            public void onItemSelected(AdapterView<?> parent, View view, int position, long id) {
                searchView.clickSearchButton();
            }
            @Override
            public void onNothingSelected(AdapterView<?> parent) {}
        });

        // Set up the checkboxes
        checkBoxAllowVariants = selfView.findViewById(R.id.check_box_allow_variants);
        loadCheckBoxes();
        CompoundButton.OnCheckedChangeListener checkBoxListener = (view, isChecked) -> {
            saveCheckBoxes();
            searchView.clickSearchButton();
        };
        checkBoxAllowVariants.setOnCheckedChangeListener(checkBoxListener);

        // Get a reference to the SearchResultFragment
        fragmentResult = (SearchResultFragment) getChildFragmentManager().findFragmentById(R.id.fragment_search_result);

        return selfView;
    }

    private void loadCheckBoxes() {
        SharedPreferences sp = PreferenceManager.getDefaultSharedPreferences(getActivity());
        Resources r = getResources();
        checkBoxAllowVariants.setChecked(sp.getBoolean(r.getString(R.string.pref_key_allow_variants), true));
    }

    private void saveCheckBoxes() {
        SharedPreferences sp = PreferenceManager.getDefaultSharedPreferences(getActivity());
        Resources r = getResources();
        sp.edit().putBoolean(r.getString(R.string.pref_key_allow_variants), checkBoxAllowVariants.isChecked()).apply();
    }

    @Override
    public void onResume() {
        super.onResume();
        refreshAdapter();
        refresh();
    }

    @Override
    public void refresh() {
        new AsyncTask<Void, Void, Cursor>() {
            @Override
            protected Cursor doInBackground(Void... params) {
                return MCPDatabase.search(getContext());
            }
            @Override
            protected void onPostExecute(Cursor data) {
                fragmentResult.setData(data);
                TextView textEmpty = fragmentResult.requireView().findViewById(android.R.id.empty);
                String query = searchView.getQuery();
                if (TextUtils.isEmpty(query)) {
                    textEmpty.setText(MCPDatabase.getIntro(getContext()));
                    textEmpty.setMovementMethod(LinkMovementMethod.getInstance());
                }
                else {
                    textEmpty.setText(R.string.no_matches);
                }
                updateResult(data);
            }
        }.execute();
    }

    private void updateResult(Cursor data) {
        TextView textResult = selfView.findViewById(R.id.result);
        AutoWebView webView = selfView.findViewById(R.id.resultRich);
        final String query = searchView.getQuery();
        int i = spinnerSearchAs.getSelectedItemPosition();
        boolean isZY = MCPDatabase.isReading(i) && query.length() >= 3
                && !Orthography.HZ.isBS(query)
                && Orthography.HZ.isHz(query);
        Map<String, String> pys = new HashMap<>();
        if (data != null && data.getCount() >= 3) {
            StringBuilder sb = new StringBuilder();
            if (isZY) {
                sb.append("<style>\n" +
                        "  @font-face {\n" +
                        "    font-family: ipa;\n" +
                        "    src: url('file:///android_res/font/ipa.ttf');\n" +
                        "  }\n" +
                        "  p {font-family: ipa, sans-serif; word-wrap: break-word;}" +
                        "    rt {font-size: 0.9em; background-color: #F0FFF0;}\n" +
                        "  </style><p>");
            }
            for (data.moveToFirst(); !data.isAfterLast(); data.moveToNext()) {
                String hz = data.getString(0);
                CharSequence py = SearchResultCursorAdapter.formatIPA(i, SearchResultCursorAdapter.getRawText(data.getString(i)));
                if (isZY) {
                    pys.put(hz, py.toString());
                } else {
                    sb.append(hz);
                }
            }
            if (isZY) {
                for (int unicode: query.codePoints().toArray()) {
                    if (!Orthography.HZ.isHz(unicode)) continue;
                    String hz = Orthography.HZ.toHz(unicode);
                    sb.append(String.format("<ruby>%s<rt>%s</rt></ruby>&nbsp;&nbsp;&nbsp;&nbsp;", hz, pys.getOrDefault(hz, "")));
                }
                webView.loadDataWithBaseURL(null, sb.toString(), "text/html", "utf-8", null);
                webView.setVisibility(View.VISIBLE);
                textResult.setVisibility(View.GONE);
            } else {
                textResult.setText(sb);
                textResult.setVisibility(View.VISIBLE);
                webView.setVisibility(View.GONE);
            }
        } else {
            textResult.setVisibility(View.GONE);
            webView.setVisibility(View.GONE);
        }
    }

    private void refreshSearchAs() {
        String lang = Utils.getLanguage(getContext());
        int index = adapter.getPosition(lang);
        if (index >= 0) spinnerSearchAs.setSelection(index);
    }

    public void refresh(String query, int mode) {
        searchView.setQuery(query);
        MCPDatabase.putColumnIndex(getContext(), mode);
        refreshSearchAs();
        refresh();
    }

    public void refreshAdapter() {
        if (adapter != null) {
            adapter.clear();
            if (MCPDatabase.getLanguages() == null) return;
            Set<String> customs = PreferenceManager.getDefaultSharedPreferences(getContext()).getStringSet(getString(R.string.pref_key_custom_languages), null);
            if (customs == null || customs.size() == 0) adapter.addAll(MCPDatabase.getLanguages());
            else {
                for (int i = 0; i < MCPDatabase.COL_JA_ANY; i++) {
                    String name = MCPDatabase.getColumnName(i);
                    if (customs.contains(name)) adapter.add(MCPDatabase.getFullName(i));
                }
            }
            //adapter.add(getString(R.string.search_as_ja_any));
            refreshSearchAs();
        }
    }
}
