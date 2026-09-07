var RikkaLAppRuntime = (() => {
  var __defProp = Object.defineProperty;
  var __getOwnPropDesc = Object.getOwnPropertyDescriptor;
  var __getOwnPropNames = Object.getOwnPropertyNames;
  var __hasOwnProp = Object.prototype.hasOwnProperty;
  var __defNormalProp = (obj, key, value) => key in obj ? __defProp(obj, key, { enumerable: true, configurable: true, writable: true, value }) : obj[key] = value;
  var __export = (target, all) => {
    for (var name in all)
      __defProp(target, name, { get: all[name], enumerable: true });
  };
  var __copyProps = (to, from, except, desc) => {
    if (from && typeof from === "object" || typeof from === "function") {
      for (let key of __getOwnPropNames(from))
        if (!__hasOwnProp.call(to, key) && key !== except)
          __defProp(to, key, { get: () => from[key], enumerable: !(desc = __getOwnPropDesc(from, key)) || desc.enumerable });
    }
    return to;
  };
  var __toCommonJS = (mod) => __copyProps(__defProp({}, "__esModule", { value: true }), mod);
  var __publicField = (obj, key, value) => __defNormalProp(obj, typeof key !== "symbol" ? key + "" : key, value);

  // .trellis/workspace/lapp-runtime-src/rikka-lapp-entry.ts
  var rikka_lapp_entry_exports = {};
  __export(rikka_lapp_entry_exports, {
    getAdapter: () => getAdapter,
    initialize: () => initialize,
    release: () => release,
    setModelInfo: () => setModelInfo
  });

  // .trellis/workspace/lapp-runtime-src/src/renderer/WebSDK/Framework/src/type/csmvector.ts
  var _csmVector = class _csmVector {
    /**
     * 引数付きコンストラクタ
     * @param iniitalCapacity 初期化後のキャパシティ。データサイズは_capacity * sizeof(T)
     * @param zeroClear trueなら初期化時に確保した領域を0で埋める
     */
    constructor(initialCapacity = 0) {
      __publicField(this, "_ptr");
      // コンテナの先頭アドレス
      __publicField(this, "_size");
      // コンテナの要素数
      __publicField(this, "_capacity");
      if (initialCapacity < 1) {
        this._ptr = [];
        this._capacity = 0;
        this._size = 0;
      } else {
        this._ptr = new Array(initialCapacity);
        this._capacity = initialCapacity;
        this._size = 0;
      }
    }
    /**
     * インデックスで指定した要素を返す
     */
    at(index) {
      return this._ptr[index];
    }
    /**
     * 要素をセット
     * @param index 要素をセットするインデックス
     * @param value セットする要素
     */
    set(index, value) {
      this._ptr[index] = value;
    }
    /**
     * コンテナを取得する
     */
    get(offset = 0) {
      const ret = new Array();
      for (let i = offset; i < this._size; i++) {
        ret.push(this._ptr[i]);
      }
      return ret;
    }
    /**
     * pushBack処理、コンテナに新たな要素を追加する
     * @param value PushBack処理で追加する値
     */
    pushBack(value) {
      if (this._size >= this._capacity) {
        this.prepareCapacity(
          this._capacity == 0 ? _csmVector.DefaultSize : this._capacity * 2
        );
      }
      this._ptr[this._size++] = value;
    }
    /**
     * コンテナの全要素を解放する
     */
    clear() {
      this._ptr.length = 0;
      this._size = 0;
    }
    /**
     * コンテナの要素数を返す
     * @return コンテナの要素数
     */
    getSize() {
      return this._size;
    }
    /**
     * コンテナの全要素に対して代入処理を行う
     * @param newSize 代入処理後のサイズ
     * @param value 要素に代入する値
     */
    assign(newSize, value) {
      const curSize = this._size;
      if (curSize < newSize) {
        this.prepareCapacity(newSize);
      }
      for (let i = 0; i < newSize; i++) {
        this._ptr[i] = value;
      }
      this._size = newSize;
    }
    /**
     * サイズ変更
     */
    resize(newSize, value = null) {
      this.updateSize(newSize, value, true);
    }
    /**
     * サイズ変更
     */
    updateSize(newSize, value = null, callPlacementNew = true) {
      const curSize = this._size;
      if (curSize < newSize) {
        this.prepareCapacity(newSize);
        if (callPlacementNew) {
          for (let i = this._size; i < newSize; i++) {
            if (typeof value == "function") {
              this._ptr[i] = JSON.parse(JSON.stringify(new value()));
            } else {
              this._ptr[i] = value;
            }
          }
        } else {
          for (let i = this._size; i < newSize; i++) {
            this._ptr[i] = value;
          }
        }
      } else {
        const sub = this._size - newSize;
        this._ptr.splice(this._size - sub, sub);
      }
      this._size = newSize;
    }
    /**
     * コンテナにコンテナ要素を挿入する
     * @param position 挿入する位置
     * @param begin 挿入するコンテナの開始位置
     * @param end 挿入するコンテナの終端位置
     */
    insert(position, begin, end) {
      let dstSi = position._index;
      const srcSi = begin._index;
      const srcEi = end._index;
      const addCount = srcEi - srcSi;
      this.prepareCapacity(this._size + addCount);
      const addSize = this._size - dstSi;
      if (addSize > 0) {
        for (let i = 0; i < addSize; i++) {
          this._ptr.splice(dstSi + i, 0, null);
        }
      }
      for (let i = srcSi; i < srcEi; i++, dstSi++) {
        this._ptr[dstSi] = begin._vector._ptr[i];
      }
      this._size = this._size + addCount;
    }
    /**
     * コンテナからインデックスで指定した要素を削除する
     * @param index インデックス値
     * @return true 削除実行
     * @return false 削除範囲外
     */
    remove(index) {
      if (index < 0 || this._size <= index) {
        return false;
      }
      this._ptr.splice(index, 1);
      --this._size;
      return true;
    }
    /**
     * コンテナから要素を削除して他の要素をシフトする
     * @param ite 削除する要素
     */
    erase(ite) {
      const index = ite._index;
      if (index < 0 || this._size <= index) {
        return ite;
      }
      this._ptr.splice(index, 1);
      --this._size;
      const ite2 = new iterator(this, index);
      return ite2;
    }
    /**
     * コンテナのキャパシティを確保する
     * @param newSize 新たなキャパシティ。引数の値が現在のサイズ未満の場合は何もしない.
     */
    prepareCapacity(newSize) {
      if (newSize > this._capacity) {
        if (this._capacity == 0) {
          this._ptr = new Array(newSize);
          this._capacity = newSize;
        } else {
          this._ptr.length = newSize;
          this._capacity = newSize;
        }
      }
    }
    /**
     * コンテナの先頭要素を返す
     */
    begin() {
      const ite = this._size == 0 ? this.end() : new iterator(this, 0);
      return ite;
    }
    /**
     * コンテナの終端要素を返す
     */
    end() {
      const ite = new iterator(this, this._size);
      return ite;
    }
    getOffset(offset) {
      const newVector = new _csmVector();
      newVector._ptr = this.get(offset);
      newVector._size = this.get(offset).length;
      newVector._capacity = this.get(offset).length;
      return newVector;
    }
    // コンテナ初期化のデフォルトサイズ
  };
  // コンテナのキャパシティ
  __publicField(_csmVector, "DefaultSize", 10);
  var csmVector = _csmVector;
  var iterator = class _iterator {
    /**
     * コンストラクタ
     */
    constructor(v, index) {
      __publicField(this, "_index");
      // コンテナのインデックス値
      __publicField(this, "_vector");
      this._vector = v != void 0 ? v : null;
      this._index = index != void 0 ? index : 0;
    }
    /**
     * 代入
     */
    set(ite) {
      this._index = ite._index;
      this._vector = ite._vector;
      return this;
    }
    /**
     * 前置き++演算
     */
    preIncrement() {
      ++this._index;
      return this;
    }
    /**
     * 前置き--演算
     */
    preDecrement() {
      --this._index;
      return this;
    }
    /**
     * 後置き++演算子
     */
    increment() {
      const iteold = new _iterator(this._vector, this._index++);
      return iteold;
    }
    /**
     * 後置き--演算子
     */
    decrement() {
      const iteold = new _iterator(this._vector, this._index--);
      return iteold;
    }
    /**
     * ptr
     */
    ptr() {
      return this._vector._ptr[this._index];
    }
    /**
     * =演算子のオーバーロード
     */
    substitution(ite) {
      this._index = ite._index;
      this._vector = ite._vector;
      return this;
    }
    /**
     * !=演算子のオーバーロード
     */
    notEqual(ite) {
      return this._index != ite._index || this._vector != ite._vector;
    }
    // コンテナ
  };
  var Live2DCubismFramework;
  ((Live2DCubismFramework42) => {
    Live2DCubismFramework42.csmVector = csmVector;
    Live2DCubismFramework42.iterator = iterator;
  })(Live2DCubismFramework || (Live2DCubismFramework = {}));

  // .trellis/workspace/lapp-runtime-src/src/renderer/WebSDK/Framework/src/type/csmstring.ts
  var csmString = class {
    /**
     * 引数付きコンストラクタ
     */
    constructor(s) {
      __publicField(this, "s");
      this.s = s;
    }
    /**
     * 文字列を後方に追加する
     *
     * @param c 追加する文字列
     * @return 更新された文字列
     */
    append(c, length) {
      this.s += length !== void 0 ? c.substr(0, length) : c;
      return this;
    }
    /**
     * 文字サイズを拡張して文字を埋める
     * @param length    拡張する文字数
     * @param v         埋める文字
     * @return 更新された文字列
     */
    expansion(length, v) {
      for (let i = 0; i < length; i++) {
        this.append(v);
      }
      return this;
    }
    /**
     * 文字列の長さをバイト数で取得する
     */
    getBytes() {
      return encodeURIComponent(this.s).replace(/%../g, "x").length;
    }
    /**
     * 文字列の長さを返す
     */
    getLength() {
      return this.s.length;
    }
    /**
     * 文字列比較 <
     * @param s 比較する文字列
     * @return true:    比較する文字列より小さい
     * @return false:   比較する文字列より大きい
     */
    isLess(s) {
      return this.s < s.s;
    }
    /**
     * 文字列比較 >
     * @param s 比較する文字列
     * @return true:    比較する文字列より大きい
     * @return false:   比較する文字列より小さい
     */
    isGreat(s) {
      return this.s > s.s;
    }
    /**
     * 文字列比較 ==
     * @param s 比較する文字列
     * @return true:    比較する文字列と等しい
     * @return false:   比較する文字列と異なる
     */
    isEqual(s) {
      return this.s == s;
    }
    /**
     * 文字列が空かどうか
     * @return true: 空の文字列
     * @return false: 値が設定されている
     */
    isEmpty() {
      return this.s.length == 0;
    }
  };
  var Live2DCubismFramework2;
  ((Live2DCubismFramework42) => {
    Live2DCubismFramework42.csmString = csmString;
  })(Live2DCubismFramework2 || (Live2DCubismFramework2 = {}));

  // .trellis/workspace/lapp-runtime-src/src/renderer/WebSDK/Framework/src/id/cubismid.ts
  var CubismId = class _CubismId {
    /**
     * プライベートコンストラクタ
     *
     * @note ユーザーによる生成は許可しません
     */
    constructor(id) {
      __publicField(this, "_id");
      if (typeof id === "string") {
        this._id = new csmString(id);
        return;
      }
      this._id = id;
    }
    /**
     * 内部で使用するCubismIdクラス生成メソッド
     *
     * @param id ID文字列
     * @returns CubismId
     * @note 指定したID文字列からCubismIdを取得する際は
     *       CubismIdManager().getId(id)を使用してください
     */
    static createIdInternal(id) {
      return new _CubismId(id);
    }
    /**
     * ID名を取得する
     */
    getString() {
      return this._id;
    }
    /**
     * idを比較
     * @param c 比較するid
     * @return 同じならばtrue,異なっていればfalseを返す
     */
    isEqual(c) {
      if (typeof c === "string") {
        return this._id.isEqual(c);
      } else if (c instanceof csmString) {
        return this._id.isEqual(c.s);
      } else if (c instanceof _CubismId) {
        return this._id.isEqual(c._id.s);
      }
      return false;
    }
    /**
     * idを比較
     * @param c 比較するid
     * @return 同じならばtrue,異なっていればfalseを返す
     */
    isNotEqual(c) {
      if (typeof c == "string") {
        return !this._id.isEqual(c);
      } else if (c instanceof csmString) {
        return !this._id.isEqual(c.s);
      } else if (c instanceof _CubismId) {
        return !this._id.isEqual(c._id.s);
      }
      return false;
    }
    // ID名
  };
  var Live2DCubismFramework3;
  ((Live2DCubismFramework42) => {
    Live2DCubismFramework42.CubismId = CubismId;
  })(Live2DCubismFramework3 || (Live2DCubismFramework3 = {}));

  // .trellis/workspace/lapp-runtime-src/src/renderer/WebSDK/Framework/src/id/cubismidmanager.ts
  var CubismIdManager = class {
    /**
     * コンストラクタ
     */
    constructor() {
      __publicField(this, "_ids");
      this._ids = new csmVector();
    }
    /**
     * デストラクタ相当の処理
     */
    release() {
      for (let i = 0; i < this._ids.getSize(); ++i) {
        this._ids.set(i, void 0);
      }
      this._ids = null;
    }
    /**
     * ID名をリストから登録
     *
     * @param ids ID名リスト
     * @param count IDの個数
     */
    registerIds(ids) {
      for (let i = 0; i < ids.length; i++) {
        this.registerId(ids[i]);
      }
    }
    /**
     * ID名を登録
     *
     * @param id ID名
     */
    registerId(id) {
      let result = null;
      if ("string" == typeof id) {
        if ((result = this.findId(id)) != null) {
          return result;
        }
        result = CubismId.createIdInternal(id);
        this._ids.pushBack(result);
      } else {
        return this.registerId(id.s);
      }
      return result;
    }
    /**
     * ID名からIDを取得する
     *
     * @param id ID名
     */
    getId(id) {
      return this.registerId(id);
    }
    /**
     * ID名からIDの確認
     *
     * @return true 存在する
     * @return false 存在しない
     */
    isExist(id) {
      if ("string" == typeof id) {
        return this.findId(id) != null;
      }
      return this.isExist(id.s);
    }
    /**
     * ID名からIDを検索する。
     *
     * @param id ID名
     * @return 登録されているID。なければNULL。
     */
    findId(id) {
      for (let i = 0; i < this._ids.getSize(); ++i) {
        if (this._ids.at(i).getString().isEqual(id)) {
          return this._ids.at(i);
        }
      }
      return null;
    }
    // 登録されているIDのリスト
  };
  var Live2DCubismFramework4;
  ((Live2DCubismFramework42) => {
    Live2DCubismFramework42.CubismIdManager = CubismIdManager;
  })(Live2DCubismFramework4 || (Live2DCubismFramework4 = {}));

  // .trellis/workspace/lapp-runtime-src/src/renderer/WebSDK/Framework/src/math/cubismmatrix44.ts
  var CubismMatrix44 = class _CubismMatrix44 {
    /**
     * コンストラクタ
     */
    constructor() {
      __publicField(this, "_tr");
      this._tr = new Float32Array(16);
      this.loadIdentity();
    }
    /**
     * 受け取った２つの行列の乗算を行う。
     *
     * @param a 行列a
     * @param b 行列b
     * @return 乗算結果の行列
     */
    static multiply(a, b, dst) {
      const c = new Float32Array([
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0
      ]);
      const n = 4;
      for (let i = 0; i < n; ++i) {
        for (let j = 0; j < n; ++j) {
          for (let k = 0; k < n; ++k) {
            c[j + i * 4] += a[k + i * 4] * b[j + k * 4];
          }
        }
      }
      for (let i = 0; i < 16; ++i) {
        dst[i] = c[i];
      }
    }
    /**
     * 単位行列に初期化する
     */
    loadIdentity() {
      const c = new Float32Array([
        1,
        0,
        0,
        0,
        0,
        1,
        0,
        0,
        0,
        0,
        1,
        0,
        0,
        0,
        0,
        1
      ]);
      this.setMatrix(c);
    }
    /**
     * 行列を設定
     *
     * @param tr 16個の浮動小数点数で表される4x4の行列
     */
    setMatrix(tr) {
      for (let i = 0; i < 16; ++i) {
        this._tr[i] = tr[i];
      }
    }
    /**
     * 行列を浮動小数点数の配列で取得
     *
     * @return 16個の浮動小数点数で表される4x4の行列
     */
    getArray() {
      return this._tr;
    }
    /**
     * X軸の拡大率を取得
     * @return X軸の拡大率
     */
    getScaleX() {
      return this._tr[0];
    }
    /**
     * Y軸の拡大率を取得する
     *
     * @return Y軸の拡大率
     */
    getScaleY() {
      return this._tr[5];
    }
    /**
     * X軸の移動量を取得
     * @return X軸の移動量
     */
    getTranslateX() {
      return this._tr[12];
    }
    /**
     * Y軸の移動量を取得
     * @return Y軸の移動量
     */
    getTranslateY() {
      return this._tr[13];
    }
    /**
     * X軸の値を現在の行列で計算
     *
     * @param src X軸の値
     * @return 現在の行列で計算されたX軸の値
     */
    transformX(src) {
      return this._tr[0] * src + this._tr[12];
    }
    /**
     * Y軸の値を現在の行列で計算
     *
     * @param src Y軸の値
     * @return 現在の行列で計算されたY軸の値
     */
    transformY(src) {
      return this._tr[5] * src + this._tr[13];
    }
    /**
     * X軸の値を現在の行列で逆計算
     */
    invertTransformX(src) {
      return (src - this._tr[12]) / this._tr[0];
    }
    /**
     * Y軸の値を現在の行列で逆計算
     */
    invertTransformY(src) {
      return (src - this._tr[13]) / this._tr[5];
    }
    /**
     * 現在の行列の位置を起点にして移動
     *
     * 現在の行列の位置を起点にして相対的に移動する。
     *
     * @param x X軸の移動量
     * @param y Y軸の移動量
     */
    translateRelative(x, y) {
      const tr1 = new Float32Array([
        1,
        0,
        0,
        0,
        0,
        1,
        0,
        0,
        0,
        0,
        1,
        0,
        x,
        y,
        0,
        1
      ]);
      _CubismMatrix44.multiply(tr1, this._tr, this._tr);
    }
    /**
     * 現在の行列の位置を移動
     *
     * 現在の行列の位置を指定した位置へ移動する
     *
     * @param x X軸の移動量
     * @param y y軸の移動量
     */
    translate(x, y) {
      this._tr[12] = x;
      this._tr[13] = y;
    }
    /**
     * 現在の行列のX軸の位置を指定した位置へ移動する
     *
     * @param x X軸の移動量
     */
    translateX(x) {
      this._tr[12] = x;
    }
    /**
     * 現在の行列のY軸の位置を指定した位置へ移動する
     *
     * @param y Y軸の移動量
     */
    translateY(y) {
      this._tr[13] = y;
    }
    /**
     * 現在の行列の拡大率を相対的に設定する
     *
     * @param x X軸の拡大率
     * @param y Y軸の拡大率
     */
    scaleRelative(x, y) {
      const tr1 = new Float32Array([
        x,
        0,
        0,
        0,
        0,
        y,
        0,
        0,
        0,
        0,
        1,
        0,
        0,
        0,
        0,
        1
      ]);
      _CubismMatrix44.multiply(tr1, this._tr, this._tr);
    }
    /**
     * 現在の行列の拡大率を指定した倍率に設定する
     *
     * @param x X軸の拡大率
     * @param y Y軸の拡大率
     */
    scale(x, y) {
      this._tr[0] = x;
      this._tr[5] = y;
    }
    /**
     * 引数で与えられた行列にこの行列を乗算する。
     * (引数で与えられた行列) * (この行列)
     *
     * @note 関数名と実際の計算内容に乖離があるため、今後計算順が修正される可能性があります。
     * @param m 行列
     */
    multiplyByMatrix(m) {
      _CubismMatrix44.multiply(m.getArray(), this._tr, this._tr);
    }
    /**
     * オブジェクトのコピーを生成する
     */
    clone() {
      const cloneMatrix = new _CubismMatrix44();
      for (let i = 0; i < this._tr.length; i++) {
        cloneMatrix._tr[i] = this._tr[i];
      }
      return cloneMatrix;
    }
    // 4x4行列データ
  };
  var Live2DCubismFramework5;
  ((Live2DCubismFramework42) => {
    Live2DCubismFramework42.CubismMatrix44 = CubismMatrix44;
  })(Live2DCubismFramework5 || (Live2DCubismFramework5 = {}));

  // .trellis/workspace/lapp-runtime-src/src/renderer/WebSDK/Framework/src/type/csmrectf.ts
  var csmRect = class {
    /**
     * コンストラクタ
     * @param x 左端X座標
     * @param y 上端Y座標
     * @param w 幅
     * @param h 高さ
     */
    constructor(x, y, w, h) {
      __publicField(this, "x");
      // 左端X座標
      __publicField(this, "y");
      // 上端Y座標
      __publicField(this, "width");
      // 幅
      __publicField(this, "height");
      this.x = x;
      this.y = y;
      this.width = w;
      this.height = h;
    }
    /**
     * 矩形中央のX座標を取得する
     */
    getCenterX() {
      return this.x + 0.5 * this.width;
    }
    /**
     * 矩形中央のY座標を取得する
     */
    getCenterY() {
      return this.y + 0.5 * this.height;
    }
    /**
     * 右側のX座標を取得する
     */
    getRight() {
      return this.x + this.width;
    }
    /**
     * 下端のY座標を取得する
     */
    getBottom() {
      return this.y + this.height;
    }
    /**
     * 矩形に値をセットする
     * @param r 矩形のインスタンス
     */
    setRect(r) {
      this.x = r.x;
      this.y = r.y;
      this.width = r.width;
      this.height = r.height;
    }
    /**
     * 矩形中央を軸にして縦横を拡縮する
     * @param w 幅方向に拡縮する量
     * @param h 高さ方向に拡縮する量
     */
    expand(w, h) {
      this.x -= w;
      this.y -= h;
      this.width += w * 2;
      this.height += h * 2;
    }
    // 高さ
  };
  var Live2DCubismFramework6;
  ((Live2DCubismFramework42) => {
    Live2DCubismFramework42.csmRect = csmRect;
  })(Live2DCubismFramework6 || (Live2DCubismFramework6 = {}));

  // .trellis/workspace/lapp-runtime-src/src/renderer/WebSDK/Framework/src/rendering/cubismrenderer.ts
  var CubismRenderer = class {
    /**
     * コンストラクタ
     */
    constructor() {
      __publicField(this, "_mvpMatrix4x4");
      // Model-View-Projection 行列
      __publicField(this, "_modelColor");
      // モデル自体のカラー（RGBA）
      __publicField(this, "_isCulling");
      // カリングが有効ならtrue
      __publicField(this, "_isPremultipliedAlpha");
      // 乗算済みαならtrue
      __publicField(this, "_anisotropy");
      // テクスチャの異方性フィルタリングのパラメータ
      __publicField(this, "_model");
      // レンダリング対象のモデル
      __publicField(this, "_useHighPrecisionMask");
      this._isCulling = false;
      this._isPremultipliedAlpha = false;
      this._anisotropy = 0;
      this._model = null;
      this._modelColor = new CubismTextureColor();
      this._useHighPrecisionMask = false;
      this._mvpMatrix4x4 = new CubismMatrix44();
      this._mvpMatrix4x4.loadIdentity();
    }
    /**
     * レンダラのインスタンスを生成して取得する
     *
     * @return レンダラのインスタンス
     */
    static create() {
      return null;
    }
    /**
     * レンダラのインスタンスを解放する
     */
    static delete(renderer) {
      renderer = null;
    }
    /**
     * レンダラの初期化処理を実行する
     * 引数に渡したモデルからレンダラの初期化処理に必要な情報を取り出すことができる
     * @param model モデルのインスタンス
     */
    initialize(model) {
      this._model = model;
    }
    /**
     * モデルを描画する
     */
    drawModel() {
      if (this.getModel() == null) return;
      this.saveProfile();
      this.doDrawModel();
      this.restoreProfile();
    }
    /**
     * Model-View-Projection 行列をセットする
     * 配列は複製されるので、元の配列は外で破棄して良い
     * @param matrix44 Model-View-Projection 行列
     */
    setMvpMatrix(matrix44) {
      this._mvpMatrix4x4.setMatrix(matrix44.getArray());
    }
    /**
     * Model-View-Projection 行列を取得する
     * @return Model-View-Projection 行列
     */
    getMvpMatrix() {
      return this._mvpMatrix4x4;
    }
    /**
     * モデルの色をセットする
     * 各色0.0~1.0の間で指定する（1.0が標準の状態）
     * @param red 赤チャンネルの値
     * @param green 緑チャンネルの値
     * @param blue 青チャンネルの値
     * @param alpha αチャンネルの値
     */
    setModelColor(red, green, blue, alpha) {
      if (red < 0) {
        red = 0;
      } else if (red > 1) {
        red = 1;
      }
      if (green < 0) {
        green = 0;
      } else if (green > 1) {
        green = 1;
      }
      if (blue < 0) {
        blue = 0;
      } else if (blue > 1) {
        blue = 1;
      }
      if (alpha < 0) {
        alpha = 0;
      } else if (alpha > 1) {
        alpha = 1;
      }
      this._modelColor.r = red;
      this._modelColor.g = green;
      this._modelColor.b = blue;
      this._modelColor.a = alpha;
    }
    /**
     * モデルの色を取得する
     * 各色0.0~1.0の間で指定する(1.0が標準の状態)
     *
     * @return RGBAのカラー情報
     */
    getModelColor() {
      return JSON.parse(JSON.stringify(this._modelColor));
    }
    /**
     * 透明度を考慮したモデルの色を計算する。
     *
     * @param opacity 透明度
     *
     * @return RGBAのカラー情報
     */
    getModelColorWithOpacity(opacity) {
      const modelColorRGBA = this.getModelColor();
      modelColorRGBA.a *= opacity;
      if (this.isPremultipliedAlpha()) {
        modelColorRGBA.r *= modelColorRGBA.a;
        modelColorRGBA.g *= modelColorRGBA.a;
        modelColorRGBA.b *= modelColorRGBA.a;
      }
      return modelColorRGBA;
    }
    /**
     * 乗算済みαの有効・無効をセットする
     * 有効にするならtrue、無効にするならfalseをセットする
     */
    setIsPremultipliedAlpha(enable) {
      this._isPremultipliedAlpha = enable;
    }
    /**
     * 乗算済みαの有効・無効を取得する
     * @return true 乗算済みのα有効
     * @return false 乗算済みのα無効
     */
    isPremultipliedAlpha() {
      return this._isPremultipliedAlpha;
    }
    /**
     * カリング（片面描画）の有効・無効をセットする。
     * 有効にするならtrue、無効にするならfalseをセットする
     */
    setIsCulling(culling) {
      this._isCulling = culling;
    }
    /**
     * カリング（片面描画）の有効・無効を取得する。
     * @return true カリング有効
     * @return false カリング無効
     */
    isCulling() {
      return this._isCulling;
    }
    /**
     * テクスチャの異方性フィルタリングのパラメータをセットする
     * パラメータ値の影響度はレンダラの実装に依存する
     * @param n パラメータの値
     */
    setAnisotropy(n) {
      this._anisotropy = n;
    }
    /**
     * テクスチャの異方性フィルタリングのパラメータをセットする
     * @return 異方性フィルタリングのパラメータ
     */
    getAnisotropy() {
      return this._anisotropy;
    }
    /**
     * レンダリングするモデルを取得する
     * @return レンダリングするモデル
     */
    getModel() {
      return this._model;
    }
    /**
     * マスク描画の方式を変更する。
     * falseの場合、マスクを1枚のテクスチャに分割してレンダリングする（デフォルト）
     * 高速だが、マスク個数の上限が36に限定され、質も荒くなる
     * trueの場合、パーツ描画の前にその都度必要なマスクを描き直す
     * レンダリング品質は高いが描画処理負荷は増す
     * @param high 高精細マスクに切り替えるか？
     */
    useHighPrecisionMask(high) {
      this._useHighPrecisionMask = high;
    }
    /**
     * マスクの描画方式を取得する
     * @return true 高精細方式
     * @return false デフォルト
     */
    isUsingHighPrecisionMask() {
      return this._useHighPrecisionMask;
    }
    // falseの場合、マスクを纏めて描画する trueの場合、マスクはパーツ描画ごとに書き直す
  };
  /**
   * レンダラが保持する静的なリソースを開放する
   */
  __publicField(CubismRenderer, "staticRelease");
  var CubismBlendMode = /* @__PURE__ */ ((CubismBlendMode2) => {
    CubismBlendMode2[CubismBlendMode2["CubismBlendMode_Normal"] = 0] = "CubismBlendMode_Normal";
    CubismBlendMode2[CubismBlendMode2["CubismBlendMode_Additive"] = 1] = "CubismBlendMode_Additive";
    CubismBlendMode2[CubismBlendMode2["CubismBlendMode_Multiplicative"] = 2] = "CubismBlendMode_Multiplicative";
    return CubismBlendMode2;
  })(CubismBlendMode || {});
  var CubismTextureColor = class {
    /**
     * コンストラクタ
     */
    constructor(r = 1, g = 1, b = 1, a = 1) {
      __publicField(this, "r");
      // 赤チャンネル
      __publicField(this, "g");
      // 緑チャンネル
      __publicField(this, "b");
      // 青チャンネル
      __publicField(this, "a");
      this.r = r;
      this.g = g;
      this.b = b;
      this.a = a;
    }
    // αチャンネル
  };
  var CubismClippingContext = class {
    /**
     * 引数付きコンストラクタ
     */
    constructor(clippingDrawableIndices, clipCount) {
      __publicField(this, "_isUsing");
      // 現在の描画状態でマスクの準備が必要ならtrue
      __publicField(this, "_clippingIdList");
      // クリッピングマスクのIDリスト
      __publicField(this, "_clippingIdCount");
      // クリッピングマスクの数
      __publicField(this, "_layoutChannelIndex");
      // RGBAのいずれのチャンネルにこのクリップを配置するか（0:R, 1:G, 2:B, 3:A）
      __publicField(this, "_layoutBounds");
      // マスク用チャンネルのどの領域にマスクを入れるか（View座標-1~1, UVは0~1に直す）
      __publicField(this, "_allClippedDrawRect");
      // このクリッピングで、クリッピングされるすべての描画オブジェクトの囲み矩形（毎回更新）
      __publicField(this, "_matrixForMask");
      // マスクの位置計算結果を保持する行列
      __publicField(this, "_matrixForDraw");
      // 描画オブジェクトの位置計算結果を保持する行列
      __publicField(this, "_clippedDrawableIndexList");
      // このマスクにクリップされる描画オブジェクトのリスト
      __publicField(this, "_bufferIndex");
      this._clippingIdList = clippingDrawableIndices;
      this._clippingIdCount = clipCount;
      this._allClippedDrawRect = new csmRect();
      this._layoutBounds = new csmRect();
      this._clippedDrawableIndexList = [];
      this._matrixForMask = new CubismMatrix44();
      this._matrixForDraw = new CubismMatrix44();
      this._bufferIndex = 0;
    }
    /**
     * デストラクタ相当の処理
     */
    release() {
      if (this._layoutBounds != null) {
        this._layoutBounds = null;
      }
      if (this._allClippedDrawRect != null) {
        this._allClippedDrawRect = null;
      }
      if (this._clippedDrawableIndexList != null) {
        this._clippedDrawableIndexList = null;
      }
    }
    /**
     * このマスクにクリップされる描画オブジェクトを追加する
     *
     * @param drawableIndex クリッピング対象に追加する描画オブジェクトのインデックス
     */
    addClippedDrawable(drawableIndex) {
      this._clippedDrawableIndexList.push(drawableIndex);
    }
    // このマスクが割り当てられるレンダーテクスチャ（フレームバッファ）やカラーバッファのインデックス
  };
  var Live2DCubismFramework7;
  ((Live2DCubismFramework42) => {
    Live2DCubismFramework42.CubismBlendMode = CubismBlendMode;
    Live2DCubismFramework42.CubismRenderer = CubismRenderer;
    Live2DCubismFramework42.CubismTextureColor = CubismTextureColor;
  })(Live2DCubismFramework7 || (Live2DCubismFramework7 = {}));

  // .trellis/workspace/lapp-runtime-src/src/renderer/WebSDK/Framework/src/cubismframeworkconfig.ts
  var CSM_LOG_LEVEL_VERBOSE = 0;
  var CSM_LOG_LEVEL_DEBUG = 1;
  var CSM_LOG_LEVEL_INFO = 2;
  var CSM_LOG_LEVEL_WARNING = 3;
  var CSM_LOG_LEVEL_ERROR = 4;
  var CSM_LOG_LEVEL = CSM_LOG_LEVEL_VERBOSE;

  // .trellis/workspace/lapp-runtime-src/src/renderer/WebSDK/Framework/src/utils/cubismdebug.ts
  var CubismLogPrint = (level, fmt, args) => {
    CubismDebug.print(level, "[CSM]" + fmt, args);
  };
  var CubismLogPrintIn = (level, fmt, args) => {
    CubismLogPrint(level, fmt + "\n", args);
  };
  var CSM_ASSERT = (expr) => {
    console.assert(expr);
  };
  var CubismLogVerbose;
  var CubismLogDebug;
  var CubismLogInfo;
  var CubismLogWarning;
  var CubismLogError;
  if (CSM_LOG_LEVEL <= CSM_LOG_LEVEL_VERBOSE) {
    CubismLogVerbose = (fmt, ...args) => {
      CubismLogPrintIn(0 /* LogLevel_Verbose */, "[V]" + fmt, args);
    };
    CubismLogDebug = (fmt, ...args) => {
      CubismLogPrintIn(1 /* LogLevel_Debug */, "[D]" + fmt, args);
    };
    CubismLogInfo = (fmt, ...args) => {
      CubismLogPrintIn(2 /* LogLevel_Info */, "[I]" + fmt, args);
    };
    CubismLogWarning = (fmt, ...args) => {
      CubismLogPrintIn(3 /* LogLevel_Warning */, "[W]" + fmt, args);
    };
    CubismLogError = (fmt, ...args) => {
      CubismLogPrintIn(4 /* LogLevel_Error */, "[E]" + fmt, args);
    };
  } else if (CSM_LOG_LEVEL == CSM_LOG_LEVEL_DEBUG) {
    CubismLogDebug = (fmt, ...args) => {
      CubismLogPrintIn(1 /* LogLevel_Debug */, "[D]" + fmt, args);
    };
    CubismLogInfo = (fmt, ...args) => {
      CubismLogPrintIn(2 /* LogLevel_Info */, "[I]" + fmt, args);
    };
    CubismLogWarning = (fmt, ...args) => {
      CubismLogPrintIn(3 /* LogLevel_Warning */, "[W]" + fmt, args);
    };
    CubismLogError = (fmt, ...args) => {
      CubismLogPrintIn(4 /* LogLevel_Error */, "[E]" + fmt, args);
    };
  } else if (CSM_LOG_LEVEL == CSM_LOG_LEVEL_INFO) {
    CubismLogInfo = (fmt, ...args) => {
      CubismLogPrintIn(2 /* LogLevel_Info */, "[I]" + fmt, args);
    };
    CubismLogWarning = (fmt, ...args) => {
      CubismLogPrintIn(3 /* LogLevel_Warning */, "[W]" + fmt, args);
    };
    CubismLogError = (fmt, ...args) => {
      CubismLogPrintIn(4 /* LogLevel_Error */, "[E]" + fmt, args);
    };
  } else if (CSM_LOG_LEVEL == CSM_LOG_LEVEL_WARNING) {
    CubismLogWarning = (fmt, ...args) => {
      CubismLogPrintIn(3 /* LogLevel_Warning */, "[W]" + fmt, args);
    };
    CubismLogError = (fmt, ...args) => {
      CubismLogPrintIn(4 /* LogLevel_Error */, "[E]" + fmt, args);
    };
  } else if (CSM_LOG_LEVEL == CSM_LOG_LEVEL_ERROR) {
    CubismLogError = (fmt, ...args) => {
      CubismLogPrintIn(4 /* LogLevel_Error */, "[E]" + fmt, args);
    };
  }
  var CubismDebug = class {
    /**
     * ログを出力する。第一引数にログレベルを設定する。
     * CubismFramework.initialize()時にオプションで設定されたログ出力レベルを下回る場合はログに出さない。
     *
     * @param logLevel ログレベルの設定
     * @param format 書式付き文字列
     * @param args 可変長引数
     */
    static print(logLevel, format, args) {
      if (logLevel < CubismFramework.getLoggingLevel()) {
        return;
      }
      const logPrint = CubismFramework.coreLogFunction;
      if (!logPrint) return;
      const buffer = format.replace(/\{(\d+)\}/g, (m, k) => {
        return args[k];
      });
      logPrint(buffer);
    }
    /**
     * データから指定した長さだけダンプ出力する。
     * CubismFramework.initialize()時にオプションで設定されたログ出力レベルを下回る場合はログに出さない。
     *
     * @param logLevel ログレベルの設定
     * @param data ダンプするデータ
     * @param length ダンプする長さ
     */
    static dumpBytes(logLevel, data, length) {
      for (let i = 0; i < length; i++) {
        if (i % 16 == 0 && i > 0) this.print(logLevel, "\n");
        else if (i % 8 == 0 && i > 0) this.print(logLevel, "  ");
        this.print(logLevel, "{0} ", [data[i] & 255]);
      }
      this.print(logLevel, "\n");
    }
    /**
     * private コンストラクタ
     */
    constructor() {
    }
  };
  var Live2DCubismFramework8;
  ((Live2DCubismFramework42) => {
    Live2DCubismFramework42.CubismDebug = CubismDebug;
  })(Live2DCubismFramework8 || (Live2DCubismFramework8 = {}));

  // .trellis/workspace/lapp-runtime-src/src/renderer/WebSDK/Framework/src/type/csmmap.ts
  var csmPair = class {
    /**
     * コンストラクタ
     * @param key Keyとしてセットする値
     * @param value Valueとしてセットする値
     */
    constructor(key, value) {
      __publicField(this, "first");
      // keyとして用いる変数
      __publicField(this, "second");
      this.first = key == void 0 ? null : key;
      this.second = value == void 0 ? null : value;
    }
    // valueとして用いる変数
  };
  var _csmMap = class _csmMap {
    /**
     * 引数付きコンストラクタ
     * @param size 初期化時点で確保するサイズ
     */
    constructor(size) {
      // コンテナの初期化のデフォルトサイズ
      __publicField(this, "_keyValues");
      // key-valueペアの配列
      __publicField(this, "_dummyValue");
      // 空の値を返す為のダミー
      __publicField(this, "_size");
      if (size != void 0) {
        if (size < 1) {
          this._keyValues = [];
          this._dummyValue = null;
          this._size = 0;
        } else {
          this._keyValues = new Array(size);
          this._size = size;
        }
      } else {
        this._keyValues = [];
        this._dummyValue = null;
        this._size = 0;
      }
    }
    /**
     * デストラクタ
     */
    release() {
      this.clear();
    }
    /**
     * キーを追加する
     * @param key 新たに追加するキー
     */
    appendKey(key) {
      this.prepareCapacity(this._size + 1, false);
      this._keyValues[this._size] = new csmPair(key);
      this._size += 1;
    }
    /**
     * 添字演算子[key]のオーバーロード(get)
     * @param key 添字から特定されるValue値
     */
    getValue(key) {
      let found = -1;
      for (let i = 0; i < this._size; i++) {
        if (this._keyValues[i].first == key) {
          found = i;
          break;
        }
      }
      if (found >= 0) {
        return this._keyValues[found].second;
      } else {
        this.appendKey(key);
        return this._keyValues[this._size - 1].second;
      }
    }
    /**
     * 添字演算子[key]のオーバーロード(set)
     * @param key 添字から特定されるValue値
     * @param value 代入するValue値
     */
    setValue(key, value) {
      let found = -1;
      for (let i = 0; i < this._size; i++) {
        if (this._keyValues[i].first == key) {
          found = i;
          break;
        }
      }
      if (found >= 0) {
        this._keyValues[found].second = value;
      } else {
        this.appendKey(key);
        this._keyValues[this._size - 1].second = value;
      }
    }
    /**
     * 引数で渡したKeyを持つ要素が存在するか
     * @param key 存在を確認するkey
     * @return true 引数で渡したkeyを持つ要素が存在する
     * @return false 引数で渡したkeyを持つ要素が存在しない
     */
    isExist(key) {
      for (let i = 0; i < this._size; i++) {
        if (this._keyValues[i].first == key) {
          return true;
        }
      }
      return false;
    }
    /**
     * keyValueのポインタを全て解放する
     */
    clear() {
      this._keyValues = void 0;
      this._keyValues = null;
      this._keyValues = [];
      this._size = 0;
    }
    /**
     * コンテナのサイズを取得する
     *
     * @return コンテナのサイズ
     */
    getSize() {
      return this._size;
    }
    /**
     * コンテナのキャパシティを確保する
     * @param newSize 新たなキャパシティ。引数の値が現在のサイズ未満の場合は何もしない。
     * @param fitToSize trueなら指定したサイズに合わせる。falseならサイズを2倍確保しておく。
     */
    prepareCapacity(newSize, fitToSize) {
      if (newSize > this._keyValues.length) {
        if (this._keyValues.length == 0) {
          if (!fitToSize && newSize < _csmMap.DefaultSize)
            newSize = _csmMap.DefaultSize;
          this._keyValues.length = newSize;
        } else {
          if (!fitToSize && newSize < this._keyValues.length * 2)
            newSize = this._keyValues.length * 2;
          this._keyValues.length = newSize;
        }
      }
    }
    /**
     * コンテナの先頭要素を返す
     */
    begin() {
      const ite = new iterator2(this, 0);
      return ite;
    }
    /**
     * コンテナの終端要素を返す
     */
    end() {
      const ite = new iterator2(
        this,
        this._size
      );
      return ite;
    }
    /**
     * コンテナから要素を削除する
     *
     * @param ite 削除する要素
     */
    erase(ite) {
      const index = ite._index;
      if (index < 0 || this._size <= index) {
        return ite;
      }
      this._keyValues.splice(index, 1);
      --this._size;
      const ite2 = new iterator2(
        this,
        index
      );
      return ite2;
    }
    /**
     * コンテナの値を32ビット符号付き整数型でダンプする
     */
    dumpAsInt() {
      for (let i = 0; i < this._size; i++) {
        CubismLogDebug("{0} ,", this._keyValues[i]);
        CubismLogDebug("\n");
      }
    }
    // コンテナの要素数
  };
  __publicField(_csmMap, "DefaultSize", 10);
  var csmMap = _csmMap;
  var iterator2 = class _iterator {
    /**
     * コンストラクタ
     */
    constructor(v, idx) {
      __publicField(this, "_index");
      // コンテナのインデックス値
      __publicField(this, "_map");
      this._map = v != void 0 ? v : new csmMap();
      this._index = idx != void 0 ? idx : 0;
    }
    /**
     * =演算子のオーバーロード
     */
    set(ite) {
      this._index = ite._index;
      this._map = ite._map;
      return this;
    }
    /**
     * 前置き++演算子のオーバーロード
     */
    preIncrement() {
      ++this._index;
      return this;
    }
    /**
     * 前置き--演算子のオーバーロード
     */
    preDecrement() {
      --this._index;
      return this;
    }
    /**
     * 後置き++演算子のオーバーロード
     */
    increment() {
      const iteold = new _iterator(this._map, this._index++);
      return iteold;
    }
    /**
     * 後置き--演算子のオーバーロード
     */
    decrement() {
      const iteold = new _iterator(this._map, this._index);
      this._map = iteold._map;
      this._index = iteold._index;
      return this;
    }
    /**
     * *演算子のオーバーロード
     */
    ptr() {
      return this._map._keyValues[this._index];
    }
    /**
     * !=演算
     */
    notEqual(ite) {
      return this._index != ite._index || this._map != ite._map;
    }
    // コンテナ
  };
  var Live2DCubismFramework9;
  ((Live2DCubismFramework42) => {
    Live2DCubismFramework42.csmMap = csmMap;
    Live2DCubismFramework42.csmPair = csmPair;
    Live2DCubismFramework42.iterator = iterator2;
  })(Live2DCubismFramework9 || (Live2DCubismFramework9 = {}));

  // .trellis/workspace/lapp-runtime-src/src/renderer/WebSDK/Framework/src/utils/cubismjsonextension.ts
  var CubismJsonExtension = class _CubismJsonExtension {
    static parseJsonObject(obj, map) {
      Object.keys(obj).forEach((key) => {
        if (typeof obj[key] == "boolean") {
          const convValue = Boolean(obj[key]);
          map.put(key, new JsonBoolean(convValue));
        } else if (typeof obj[key] == "string") {
          const convValue = String(obj[key]);
          map.put(key, new JsonString(convValue));
        } else if (typeof obj[key] == "number") {
          const convValue = Number(obj[key]);
          map.put(key, new JsonFloat(convValue));
        } else if (obj[key] instanceof Array) {
          map.put(key, _CubismJsonExtension.parseJsonArray(obj[key]));
        } else if (obj[key] instanceof Object) {
          map.put(
            key,
            _CubismJsonExtension.parseJsonObject(obj[key], new JsonMap())
          );
        } else if (obj[key] == null) {
          map.put(key, new JsonNullvalue());
        } else {
          map.put(key, obj[key]);
        }
      });
      return map;
    }
    static parseJsonArray(obj) {
      const arr = new JsonArray();
      Object.keys(obj).forEach((key) => {
        const convKey = Number(key);
        if (typeof convKey == "number") {
          if (typeof obj[key] == "boolean") {
            const convValue = Boolean(obj[key]);
            arr.add(new JsonBoolean(convValue));
          } else if (typeof obj[key] == "string") {
            const convValue = String(obj[key]);
            arr.add(new JsonString(convValue));
          } else if (typeof obj[key] == "number") {
            const convValue = Number(obj[key]);
            arr.add(new JsonFloat(convValue));
          } else if (obj[key] instanceof Array) {
            arr.add(this.parseJsonArray(obj[key]));
          } else if (obj[key] instanceof Object) {
            arr.add(this.parseJsonObject(obj[key], new JsonMap()));
          } else if (obj[key] == null) {
            arr.add(new JsonNullvalue());
          } else {
            arr.add(obj[key]);
          }
        } else if (obj[key] instanceof Array) {
          arr.add(this.parseJsonArray(obj[key]));
        } else if (obj[key] instanceof Object) {
          arr.add(this.parseJsonObject(obj[key], new JsonMap()));
        } else if (obj[key] == null) {
          arr.add(new JsonNullvalue());
        } else {
          const convValue = Array(obj[key]);
          for (let i = 0; i < convValue.length; i++) {
            arr.add(convValue[i]);
          }
        }
      });
      return arr;
    }
  };

  // .trellis/workspace/lapp-runtime-src/src/renderer/WebSDK/Framework/src/utils/cubismjson.ts
  var CSM_JSON_ERROR_TYPE_MISMATCH = "Error: type mismatch";
  var CSM_JSON_ERROR_INDEX_OF_BOUNDS = "Error: index out of bounds";
  var _Value = class _Value {
    /**
     * コンストラクタ
     */
    constructor() {
      __publicField(this, "_stringBuffer");
    }
    /**
     * 要素を文字列型で返す(string)
     */
    getRawString(defaultValue, indent) {
      return this.getString(defaultValue, indent);
    }
    /**
     * 要素を数値型で返す(number)
     */
    toInt(defaultValue = 0) {
      return defaultValue;
    }
    /**
     * 要素を数値型で返す(number)
     */
    toFloat(defaultValue = 0) {
      return defaultValue;
    }
    /**
     * 要素を真偽値で返す(boolean)
     */
    toBoolean(defaultValue = false) {
      return defaultValue;
    }
    /**
     * サイズを返す
     */
    getSize() {
      return 0;
    }
    /**
     * 要素を配列で返す(Value[])
     */
    getArray(defaultValue = null) {
      return defaultValue;
    }
    /**
     * 要素をコンテナで返す(array)
     */
    getVector(defaultValue = new csmVector()) {
      return defaultValue;
    }
    /**
     * 要素をマップで返す(csmMap<csmString, Value>)
     */
    getMap(defaultValue) {
      return defaultValue;
    }
    /**
     * 添字演算子[index]
     */
    getValueByIndex(index) {
      return _Value.errorValue.setErrorNotForClientCall(
        CSM_JSON_ERROR_TYPE_MISMATCH
      );
    }
    /**
     * 添字演算子[string | csmString]
     */
    getValueByString(s) {
      return _Value.nullValue.setErrorNotForClientCall(
        CSM_JSON_ERROR_TYPE_MISMATCH
      );
    }
    /**
     * マップのキー一覧をコンテナで返す
     *
     * @return マップのキーの一覧
     */
    getKeys() {
      return _Value.dummyKeys;
    }
    /**
     * Valueの種類がエラー値ならtrue
     */
    isError() {
      return false;
    }
    /**
     * Valueの種類がnullならtrue
     */
    isNull() {
      return false;
    }
    /**
     * Valueの種類が真偽値ならtrue
     */
    isBool() {
      return false;
    }
    /**
     * Valueの種類が数値型ならtrue
     */
    isFloat() {
      return false;
    }
    /**
     * Valueの種類が文字列ならtrue
     */
    isString() {
      return false;
    }
    /**
     * Valueの種類が配列ならtrue
     */
    isArray() {
      return false;
    }
    /**
     * Valueの種類がマップ型ならtrue
     */
    isMap() {
      return false;
    }
    equals(value) {
      return false;
    }
    /**
     * Valueの値が静的ならtrue、静的なら解放しない
     */
    isStatic() {
      return false;
    }
    /**
     * Valueにエラー値をセットする
     */
    setErrorNotForClientCall(errorStr) {
      return JsonError.errorValue;
    }
    /**
     * 初期化用メソッド
     */
    static staticInitializeNotForClientCall() {
      JsonBoolean.trueValue = new JsonBoolean(true);
      JsonBoolean.falseValue = new JsonBoolean(false);
      _Value.errorValue = new JsonError("ERROR", true);
      _Value.nullValue = new JsonNullvalue();
      _Value.dummyKeys = new csmVector();
    }
    /**
     * リリース用メソッド
     */
    static staticReleaseNotForClientCall() {
      JsonBoolean.trueValue = null;
      JsonBoolean.falseValue = null;
      _Value.errorValue = null;
      _Value.nullValue = null;
      _Value.dummyKeys = null;
    }
    // 明示的に連想配列をany型で指定
  };
  // 文字列バッファ
  __publicField(_Value, "dummyKeys");
  // ダミーキー
  __publicField(_Value, "errorValue");
  // 一時的な返り値として返すエラー。 CubismFramework::Disposeするまではdeleteしない
  __publicField(_Value, "nullValue");
  var Value2 = _Value;
  var CubismJson = class _CubismJson {
    /**
     * コンストラクタ
     */
    constructor(buffer, length) {
      __publicField(this, "_parseCallback", CubismJsonExtension.parseJsonObject);
      // パース時に使う処理のコールバック関数
      __publicField(this, "_error");
      // パース時のエラー
      __publicField(this, "_lineCount");
      // エラー報告に用いる行数カウント
      __publicField(this, "_root");
      this._error = null;
      this._lineCount = 0;
      this._root = null;
      if (buffer != void 0) {
        this.parseBytes(buffer, length, this._parseCallback);
      }
    }
    /**
     * バイトデータから直接ロードしてパースする
     *
     * @param buffer バッファ
     * @param size バッファサイズ
     * @return CubismJsonクラスのインスタンス。失敗したらNULL
     */
    static create(buffer, size) {
      const json = new _CubismJson();
      const succeeded = json.parseBytes(
        buffer,
        size,
        json._parseCallback
      );
      if (!succeeded) {
        _CubismJson.delete(json);
        return null;
      } else {
        return json;
      }
    }
    /**
     * パースしたJSONオブジェクトの解放処理
     *
     * @param instance CubismJsonクラスのインスタンス
     */
    static delete(instance) {
      instance = null;
    }
    /**
     * パースしたJSONのルート要素を返す
     */
    getRoot() {
      return this._root;
    }
    /**
     *  UnicodeのバイナリをStringに変換
     *
     * @param buffer 変換するバイナリデータ
     * @return 変換後の文字列
     */
    static arrayBufferToString(buffer) {
      const uint8Array = new Uint8Array(buffer);
      let str = "";
      for (let i = 0, len = uint8Array.length; i < len; ++i) {
        str += "%" + this.pad(uint8Array[i].toString(16));
      }
      str = decodeURIComponent(str);
      return str;
    }
    /**
     * エンコード、パディング
     */
    static pad(n) {
      return n.length < 2 ? "0" + n : n;
    }
    /**
     * JSONのパースを実行する
     * @param buffer    パース対象のデータバイト
     * @param size      データバイトのサイズ
     * return true : 成功
     * return false: 失敗
     */
    parseBytes(buffer, size, parseCallback) {
      const endPos = new Array(1);
      const decodeBuffer = _CubismJson.arrayBufferToString(buffer);
      if (parseCallback == void 0) {
        this._root = this.parseValue(decodeBuffer, size, 0, endPos);
      } else {
        this._root = parseCallback(JSON.parse(decodeBuffer), new JsonMap());
      }
      if (this._error) {
        let strbuf = "\0";
        strbuf = "Json parse error : @line " + (this._lineCount + 1) + "\n";
        this._root = new JsonString(strbuf);
        CubismLogInfo("{0}", this._root.getRawString());
        return false;
      } else if (this._root == null) {
        this._root = new JsonError(new csmString(this._error), false);
        return false;
      }
      return true;
    }
    /**
     * パース時のエラー値を返す
     */
    getParseError() {
      return this._error;
    }
    /**
     * ルート要素の次の要素がファイルの終端だったらtrueを返す
     */
    checkEndOfFile() {
      return this._root.getArray()[1].equals("EOF");
    }
    /**
     * JSONエレメントからValue(float,String,Value*,Array,null,true,false)をパースする
     * エレメントの書式に応じて内部でParseString(), ParseObject(), ParseArray()を呼ぶ
     *
     * @param   buffer      JSONエレメントのバッファ
     * @param   length      パースする長さ
     * @param   begin       パースを開始する位置
     * @param   outEndPos   パース終了時の位置
     * @return      パースから取得したValueオブジェクト
     */
    parseValue(buffer, length, begin, outEndPos) {
      if (this._error) return null;
      let o = null;
      let i = begin;
      let f;
      for (; i < length; i++) {
        const c = buffer[i];
        switch (c) {
          case "-":
          case ".":
          case "0":
          case "1":
          case "2":
          case "3":
          case "4":
          case "5":
          case "6":
          case "7":
          case "8":
          case "9": {
            const afterString = new Array(1);
            f = strtod(buffer.slice(i), afterString);
            outEndPos[0] = buffer.indexOf(afterString[0]);
            return new JsonFloat(f);
          }
          case '"':
            return new JsonString(
              this.parseString(buffer, length, i + 1, outEndPos)
            );
          // \"の次の文字から
          case "[":
            o = this.parseArray(buffer, length, i + 1, outEndPos);
            return o;
          case "{":
            o = this.parseObject(buffer, length, i + 1, outEndPos);
            return o;
          case "n":
            if (i + 3 < length) {
              o = new JsonNullvalue();
              outEndPos[0] = i + 4;
            } else {
              this._error = "parse null";
            }
            return o;
          case "t":
            if (i + 3 < length) {
              o = JsonBoolean.trueValue;
              outEndPos[0] = i + 4;
            } else {
              this._error = "parse true";
            }
            return o;
          case "f":
            if (i + 4 < length) {
              o = JsonBoolean.falseValue;
              outEndPos[0] = i + 5;
            } else {
              this._error = "illegal ',' position";
            }
            return o;
          case ",":
            this._error = "illegal ',' position";
            return null;
          case "]":
            outEndPos[0] = i;
            return null;
          case "\n":
            this._lineCount++;
          // falls through
          case " ":
          case "	":
          case "\r":
          default:
            break;
        }
      }
      this._error = "illegal end of value";
      return null;
    }
    /**
     * 次の「"」までの文字列をパースする。
     *
     * @param   string  ->  パース対象の文字列
     * @param   length  ->  パースする長さ
     * @param   begin   ->  パースを開始する位置
     * @param  outEndPos   ->  パース終了時の位置
     * @return      パースした文F字列要素
     */
    parseString(string, length, begin, outEndPos) {
      if (this._error) {
        return null;
      }
      if (!string) {
        this._error = "string is null";
        return null;
      }
      let i = begin;
      let c, c2;
      const ret = new csmString("");
      let bufStart = begin;
      for (; i < length; i++) {
        c = string[i];
        switch (c) {
          case '"': {
            outEndPos[0] = i + 1;
            ret.append(string.slice(bufStart), i - bufStart);
            return ret.s;
          }
          // falls through
          case "//": {
            i++;
            if (i - 1 > bufStart) {
              ret.append(string.slice(bufStart), i - bufStart);
            }
            bufStart = i + 1;
            if (i < length) {
              c2 = string[i];
              switch (c2) {
                case "\\":
                  ret.expansion(1, "\\");
                  break;
                case '"':
                  ret.expansion(1, '"');
                  break;
                case "/":
                  ret.expansion(1, "/");
                  break;
                case "b":
                  ret.expansion(1, "\b");
                  break;
                case "f":
                  ret.expansion(1, "\f");
                  break;
                case "n":
                  ret.expansion(1, "\n");
                  break;
                case "r":
                  ret.expansion(1, "\r");
                  break;
                case "t":
                  ret.expansion(1, "	");
                  break;
                case "u":
                  this._error = "parse string/unicord escape not supported";
                  break;
                default:
                  break;
              }
            } else {
              this._error = "parse string/escape error";
            }
          }
          // falls through
          default: {
            break;
          }
        }
      }
      this._error = "parse string/illegal end";
      return null;
    }
    /**
     * JSONのオブジェクトエレメントをパースしてValueオブジェクトを返す
     *
     * @param buffer    JSONエレメントのバッファ
     * @param length    パースする長さ
     * @param begin     パースを開始する位置
     * @param outEndPos パース終了時の位置
     * @return パースから取得したValueオブジェクト
     */
    parseObject(buffer, length, begin, outEndPos) {
      if (this._error) {
        return null;
      }
      if (!buffer) {
        this._error = "buffer is null";
        return null;
      }
      const ret = new JsonMap();
      let key = "";
      let i = begin;
      let c = "";
      const localRetEndPos2 = Array(1);
      let ok = false;
      for (; i < length; i++) {
        FOR_LOOP: for (; i < length; i++) {
          c = buffer[i];
          switch (c) {
            case '"':
              key = this.parseString(buffer, length, i + 1, localRetEndPos2);
              if (this._error) {
                return null;
              }
              i = localRetEndPos2[0];
              ok = true;
              break FOR_LOOP;
            //-- loopから出る
            case "}":
              outEndPos[0] = i + 1;
              return ret;
            // 空
            case ":":
              this._error = "illegal ':' position";
              break;
            case "\n":
              this._lineCount++;
            // falls through
            default:
              break;
          }
        }
        if (!ok) {
          this._error = "key not found";
          return null;
        }
        ok = false;
        FOR_LOOP2: for (; i < length; i++) {
          c = buffer[i];
          switch (c) {
            case ":":
              ok = true;
              i++;
              break FOR_LOOP2;
            case "}":
              this._error = "illegal '}' position";
              break;
            // falls through
            case "\n":
              this._lineCount++;
            // case ' ': case '\t' : case '\r':
            // falls through
            default:
              break;
          }
        }
        if (!ok) {
          this._error = "':' not found";
          return null;
        }
        const value = this.parseValue(buffer, length, i, localRetEndPos2);
        if (this._error) {
          return null;
        }
        i = localRetEndPos2[0];
        ret.put(key, value);
        FOR_LOOP3: for (; i < length; i++) {
          c = buffer[i];
          switch (c) {
            case ",":
              break FOR_LOOP3;
            case "}":
              outEndPos[0] = i + 1;
              return ret;
            // 正常終了
            case "\n":
              this._lineCount++;
            // falls through
            default:
              break;
          }
        }
      }
      this._error = "illegal end of perseObject";
      return null;
    }
    /**
     * 次の「"」までの文字列をパースする。
     * @param buffer    JSONエレメントのバッファ
     * @param length    パースする長さ
     * @param begin     パースを開始する位置
     * @param outEndPos パース終了時の位置
     * @return パースから取得したValueオブジェクト
     */
    parseArray(buffer, length, begin, outEndPos) {
      if (this._error) {
        return null;
      }
      if (!buffer) {
        this._error = "buffer is null";
        return null;
      }
      let ret = new JsonArray();
      let i = begin;
      let c;
      const localRetEndpos2 = new Array(1);
      for (; i < length; i++) {
        const value = this.parseValue(buffer, length, i, localRetEndpos2);
        if (this._error) {
          return null;
        }
        i = localRetEndpos2[0];
        if (value) {
          ret.add(value);
        }
        FOR_LOOP: for (; i < length; i++) {
          c = buffer[i];
          switch (c) {
            case ",":
              break FOR_LOOP;
            case "]":
              outEndPos[0] = i + 1;
              return ret;
            // 終了
            case "\n":
              ++this._lineCount;
            //case ' ': case '\t': case '\r':
            // falls through
            default:
              break;
          }
        }
      }
      ret = void 0;
      this._error = "illegal end of parseObject";
      return null;
    }
    // パースされたルート要素
  };
  var JsonFloat = class extends Value2 {
    /**
     * コンストラクタ
     */
    constructor(v) {
      super();
      __publicField(this, "_value");
      this._value = v;
    }
    /**
     * Valueの種類が数値型ならtrue
     */
    isFloat() {
      return true;
    }
    /**
     * 要素を文字列で返す(csmString型)
     */
    getString(defaultValue, indent) {
      const strbuf = "\0";
      this._value = parseFloat(strbuf);
      this._stringBuffer = strbuf;
      return this._stringBuffer;
    }
    /**
     * 要素を数値型で返す(number)
     */
    toInt(defaultValue = 0) {
      return parseInt(this._value.toString());
    }
    /**
     * 要素を数値型で返す(number)
     */
    toFloat(defaultValue = 0) {
      return this._value;
    }
    equals(value) {
      if ("number" === typeof value) {
        if (Math.round(value)) {
          return false;
        } else {
          return value == this._value;
        }
      }
      return false;
    }
    // JSON要素の値
  };
  var JsonBoolean = class extends Value2 {
    /**
     * 引数付きコンストラクタ
     */
    constructor(v) {
      super();
      // false
      __publicField(this, "_boolValue");
      this._boolValue = v;
    }
    /**
     * Valueの種類が真偽値ならtrue
     */
    isBool() {
      return true;
    }
    /**
     * 要素を真偽値で返す(boolean)
     */
    toBoolean(defaultValue = false) {
      return this._boolValue;
    }
    /**
     * 要素を文字列で返す(csmString型)
     */
    getString(defaultValue, indent) {
      this._stringBuffer = this._boolValue ? "true" : "false";
      return this._stringBuffer;
    }
    equals(value) {
      if ("boolean" === typeof value) {
        return value == this._boolValue;
      }
      return false;
    }
    /**
     * Valueの値が静的ならtrue, 静的なら解放しない
     */
    isStatic() {
      return true;
    }
    // JSON要素の値
  };
  __publicField(JsonBoolean, "trueValue");
  // true
  __publicField(JsonBoolean, "falseValue");
  var JsonString = class extends Value2 {
    constructor(s) {
      super();
      if ("string" === typeof s) {
        this._stringBuffer = s;
      }
      if (s instanceof csmString) {
        this._stringBuffer = s.s;
      }
    }
    /**
     * Valueの種類が文字列ならtrue
     */
    isString() {
      return true;
    }
    /**
     * 要素を文字列で返す(csmString型)
     */
    getString(defaultValue, indent) {
      return this._stringBuffer;
    }
    equals(value) {
      if ("string" === typeof value) {
        return this._stringBuffer == value;
      }
      if (value instanceof csmString) {
        return this._stringBuffer == value.s;
      }
      return false;
    }
  };
  var JsonError = class extends JsonString {
    /**
     * 引数付きコンストラクタ
     */
    constructor(s, isStatic) {
      var __super = (...args) => {
        super(...args);
        __publicField(this, "_isStatic");
        return this;
      };
      if ("string" === typeof s) {
        __super(s);
      } else {
        __super(s);
      }
      this._isStatic = isStatic;
    }
    /**
     * Valueの値が静的ならtrue、静的なら解放しない
     */
    isStatic() {
      return this._isStatic;
    }
    /**
     * エラー情報をセットする
     */
    setErrorNotForClientCall(s) {
      this._stringBuffer = s;
      return this;
    }
    /**
     * Valueの種類がエラー値ならtrue
     */
    isError() {
      return true;
    }
    // 静的なValueかどうか
  };
  var JsonNullvalue = class extends Value2 {
    /**
     * Valueの種類がNULL値ならtrue
     */
    isNull() {
      return true;
    }
    /**
     * 要素を文字列で返す(csmString型)
     */
    getString(defaultValue, indent) {
      return this._stringBuffer;
    }
    /**
     * Valueの値が静的ならtrue, 静的なら解放しない
     */
    isStatic() {
      return true;
    }
    /**
     * Valueにエラー値をセットする
     */
    setErrorNotForClientCall(s) {
      this._stringBuffer = s;
      return JsonError.nullValue;
    }
    /**
     * コンストラクタ
     */
    constructor() {
      super();
      this._stringBuffer = "NullValue";
    }
  };
  var JsonArray = class extends Value2 {
    /**
     * コンストラクタ
     */
    constructor() {
      super();
      __publicField(this, "_array");
      this._array = new csmVector();
    }
    /**
     * デストラクタ相当の処理
     */
    release() {
      for (let ite = this._array.begin(); ite.notEqual(this._array.end()); ite.preIncrement()) {
        let v = ite.ptr();
        if (v && !v.isStatic()) {
          v = void 0;
          v = null;
        }
      }
    }
    /**
     * Valueの種類が配列ならtrue
     */
    isArray() {
      return true;
    }
    /**
     * 添字演算子[index]
     */
    getValueByIndex(index) {
      if (index < 0 || this._array.getSize() <= index) {
        return Value2.errorValue.setErrorNotForClientCall(
          CSM_JSON_ERROR_INDEX_OF_BOUNDS
        );
      }
      const v = this._array.at(index);
      if (v == null) {
        return Value2.nullValue;
      }
      return v;
    }
    /**
     * 添字演算子[string | csmString]
     */
    getValueByString(s) {
      return Value2.errorValue.setErrorNotForClientCall(
        CSM_JSON_ERROR_TYPE_MISMATCH
      );
    }
    /**
     * 要素を文字列で返す(csmString型)
     */
    getString(defaultValue, indent) {
      const stringBuffer = indent + "[\n";
      for (let ite = this._array.begin(); ite.notEqual(this._array.end()); ite.increment()) {
        const v = ite.ptr();
        this._stringBuffer += indent + "" + v.getString(indent + " ") + "\n";
      }
      this._stringBuffer = stringBuffer + indent + "]\n";
      return this._stringBuffer;
    }
    /**
     * 配列要素を追加する
     * @param v 追加する要素
     */
    add(v) {
      this._array.pushBack(v);
    }
    /**
     * 要素をコンテナで返す(csmVector<Value>)
     */
    getVector(defaultValue = null) {
      return this._array;
    }
    /**
     * 要素の数を返す
     */
    getSize() {
      return this._array.getSize();
    }
    // JSON要素の値
  };
  var JsonMap = class extends Value2 {
    /**
     * コンストラクタ
     */
    constructor() {
      super();
      __publicField(this, "_map");
      // JSON要素の値
      __publicField(this, "_keys");
      this._map = new csmMap();
    }
    /**
     * デストラクタ相当の処理
     */
    release() {
      const ite = this._map.begin();
      while (ite.notEqual(this._map.end())) {
        let v = ite.ptr().second;
        if (v && !v.isStatic()) {
          v = void 0;
          v = null;
        }
        ite.preIncrement();
      }
    }
    /**
     * Valueの値がMap型ならtrue
     */
    isMap() {
      return true;
    }
    /**
     * 添字演算子[string | csmString]
     */
    getValueByString(s) {
      if (s instanceof csmString) {
        const ret = this._map.getValue(s.s);
        if (ret == null) {
          return Value2.nullValue;
        }
        return ret;
      }
      for (let iter = this._map.begin(); iter.notEqual(this._map.end()); iter.preIncrement()) {
        if (iter.ptr().first == s) {
          if (iter.ptr().second == null) {
            return Value2.nullValue;
          }
          return iter.ptr().second;
        }
      }
      return Value2.nullValue;
    }
    /**
     * 添字演算子[index]
     */
    getValueByIndex(index) {
      return Value2.errorValue.setErrorNotForClientCall(
        CSM_JSON_ERROR_TYPE_MISMATCH
      );
    }
    /**
     * 要素を文字列で返す(csmString型)
     */
    getString(defaultValue, indent) {
      this._stringBuffer = indent + "{\n";
      const ite = this._map.begin();
      while (ite.notEqual(this._map.end())) {
        const key = ite.ptr().first;
        const v = ite.ptr().second;
        this._stringBuffer += indent + " " + key + " : " + v.getString(indent + "   ") + " \n";
        ite.preIncrement();
      }
      this._stringBuffer += indent + "}\n";
      return this._stringBuffer;
    }
    /**
     * 要素をMap型で返す
     */
    getMap(defaultValue) {
      return this._map;
    }
    /**
     * Mapに要素を追加する
     */
    put(key, v) {
      this._map.setValue(key, v);
    }
    /**
     * Mapからキーのリストを取得する
     */
    getKeys() {
      if (!this._keys) {
        this._keys = new csmVector();
        const ite = this._map.begin();
        while (ite.notEqual(this._map.end())) {
          const key = ite.ptr().first;
          this._keys.pushBack(key);
          ite.preIncrement();
        }
      }
      return this._keys;
    }
    /**
     * Mapの要素数を取得する
     */
    getSize() {
      return this._keys.getSize();
    }
    // JSON要素の値
  };
  var Live2DCubismFramework10;
  ((Live2DCubismFramework42) => {
    Live2DCubismFramework42.CubismJson = CubismJson;
    Live2DCubismFramework42.JsonArray = JsonArray;
    Live2DCubismFramework42.JsonBoolean = JsonBoolean;
    Live2DCubismFramework42.JsonError = JsonError;
    Live2DCubismFramework42.JsonFloat = JsonFloat;
    Live2DCubismFramework42.JsonMap = JsonMap;
    Live2DCubismFramework42.JsonNullvalue = JsonNullvalue;
    Live2DCubismFramework42.JsonString = JsonString;
    Live2DCubismFramework42.Value = Value2;
  })(Live2DCubismFramework10 || (Live2DCubismFramework10 = {}));

  // .trellis/workspace/lapp-runtime-src/src/renderer/WebSDK/Framework/src/live2dcubismframework.ts
  function strtod(s, endPtr) {
    let index = 0;
    for (let i = 1; ; i++) {
      const testC = s.slice(i - 1, i);
      if (testC == "e" || testC == "-" || testC == "E") {
        continue;
      }
      const test = s.substring(0, i);
      const number = Number(test);
      if (isNaN(number)) {
        break;
      }
      index = i;
    }
    let d = parseFloat(s);
    if (isNaN(d)) {
      d = NaN;
    }
    endPtr[0] = s.slice(index);
    return d;
  }
  var s_isStarted = false;
  var s_isInitialized = false;
  var s_option = null;
  var s_cubismIdManager = null;
  var Constant = Object.freeze({
    vertexOffset: 0,
    // メッシュ頂点のオフセット値
    vertexStep: 2
    // メッシュ頂点のステップ値
  });
  function csmDelete(address) {
    if (!address) {
      return;
    }
    address = void 0;
  }
  var CubismFramework = class {
    /**
     * Cubism FrameworkのAPIを使用可能にする。
     *  APIを実行する前に必ずこの関数を実行すること。
     *  一度準備が完了して以降は、再び実行しても内部処理がスキップされます。
     *
     * @param    option      Optionクラスのインスタンス
     *
     * @return   準備処理が完了したらtrueが返ります。
     */
    static startUp(option = null) {
      if (s_isStarted) {
        CubismLogInfo("CubismFramework.startUp() is already done.");
        return s_isStarted;
      }
      s_option = option;
      if (s_option != null) {
        Live2DCubismCore.Logging.csmSetLogFunction(s_option.logFunction);
      }
      s_isStarted = true;
      if (s_isStarted) {
        const version = Live2DCubismCore.Version.csmGetVersion();
        const major = (version & 4278190080) >> 24;
        const minor = (version & 16711680) >> 16;
        const patch = version & 65535;
        const versionNumber = version;
        CubismLogInfo(
          `Live2D Cubism Core version: {0}.{1}.{2} ({3})`,
          ("00" + major).slice(-2),
          ("00" + minor).slice(-2),
          ("0000" + patch).slice(-4),
          versionNumber
        );
      }
      CubismLogInfo("CubismFramework.startUp() is complete.");
      return s_isStarted;
    }
    /**
     * StartUp()で初期化したCubismFrameworkの各パラメータをクリアします。
     * Dispose()したCubismFrameworkを再利用する際に利用してください。
     */
    static cleanUp() {
      s_isStarted = false;
      s_isInitialized = false;
      s_option = null;
      s_cubismIdManager = null;
    }
    /**
     * Cubism Framework内のリソースを初期化してモデルを表示可能な状態にします。<br>
     *     再度Initialize()するには先にDispose()を実行する必要があります。
     *
     * @param memorySize 初期化時メモリ量 [byte(s)]
     *    複数モデル表示時などにモデルが更新されない際に使用してください。
     *    指定する際は必ず1024*1024*16 byte(16MB)以上の値を指定してください。
     *    それ以外はすべて1024*1024*16 byteに丸めます。
     */
    static initialize(memorySize = 0) {
      CSM_ASSERT(s_isStarted);
      if (!s_isStarted) {
        CubismLogWarning("CubismFramework is not started.");
        return;
      }
      if (s_isInitialized) {
        CubismLogWarning(
          "CubismFramework.initialize() skipped, already initialized."
        );
        return;
      }
      Value2.staticInitializeNotForClientCall();
      s_cubismIdManager = new CubismIdManager();
      Live2DCubismCore.Memory.initializeAmountOfMemory(memorySize);
      s_isInitialized = true;
      CubismLogInfo("CubismFramework.initialize() is complete.");
    }
    /**
     * Cubism Framework内の全てのリソースを解放します。
     *      ただし、外部で確保されたリソースについては解放しません。
     *      外部で適切に破棄する必要があります。
     */
    static dispose() {
      CSM_ASSERT(s_isStarted);
      if (!s_isStarted) {
        CubismLogWarning("CubismFramework is not started.");
        return;
      }
      if (!s_isInitialized) {
        CubismLogWarning("CubismFramework.dispose() skipped, not initialized.");
        return;
      }
      Value2.staticReleaseNotForClientCall();
      s_cubismIdManager.release();
      s_cubismIdManager = null;
      CubismRenderer.staticRelease();
      s_isInitialized = false;
      CubismLogInfo("CubismFramework.dispose() is complete.");
    }
    /**
     * Cubism FrameworkのAPIを使用する準備が完了したかどうか
     * @return APIを使用する準備が完了していればtrueが返ります。
     */
    static isStarted() {
      return s_isStarted;
    }
    /**
     * Cubism Frameworkのリソース初期化がすでに行われているかどうか
     * @return リソース確保が完了していればtrueが返ります
     */
    static isInitialized() {
      return s_isInitialized;
    }
    /**
     * Core APIにバインドしたログ関数を実行する
     *
     * @praram message ログメッセージ
     */
    static coreLogFunction(message) {
      if (!Live2DCubismCore.Logging.csmGetLogFunction()) {
        return;
      }
      Live2DCubismCore.Logging.csmGetLogFunction()(message);
    }
    /**
     * 現在のログ出力レベル設定の値を返す。
     *
     * @return  現在のログ出力レベル設定の値
     */
    static getLoggingLevel() {
      if (s_option != null) {
        return s_option.loggingLevel;
      }
      return 5 /* LogLevel_Off */;
    }
    /**
     * IDマネージャのインスタンスを取得する
     * @return CubismManagerクラスのインスタンス
     */
    static getIdManager() {
      return s_cubismIdManager;
    }
    /**
     * 静的クラスとして使用する
     * インスタンス化させない
     */
    constructor() {
    }
  };
  var Option = class {
    constructor() {
      __publicField(this, "logFunction");
      // ログ出力の関数オブジェクト
      __publicField(this, "loggingLevel");
    }
    // ログ出力レベルの設定
  };
  var Live2DCubismFramework11;
  ((Live2DCubismFramework42) => {
    Live2DCubismFramework42.Constant = Constant;
    Live2DCubismFramework42.csmDelete = csmDelete;
    Live2DCubismFramework42.CubismFramework = CubismFramework;
  })(Live2DCubismFramework11 || (Live2DCubismFramework11 = {}));

  // .trellis/workspace/lapp-runtime-src/src/renderer/WebSDK/src/lappdefine.ts
  var CanvasSize = "auto";
  var ViewScale = 1;
  var CurrentKScale = ViewScale;
  var ViewMaxScale = 2;
  var ViewMinScale = 0.8;
  var ViewLogicalLeft = -1;
  var ViewLogicalRight = 1;
  var ViewLogicalMaxLeft = -2;
  var ViewLogicalMaxRight = 2;
  var ViewLogicalMaxBottom = -2;
  var ViewLogicalMaxTop = 2;
  var ResourcesPath = "";
  var ModelDir = [];
  var ModelFileNames = [];
  function updateModelConfig(resourcePath, modelDirectory, modelFileName, kScale) {
    console.log("Updating model config:", { resourcePath, modelDirectory, modelFileName, kScale });
    ResourcesPath = resourcePath;
    ModelDir = [modelDirectory];
    ModelFileNames = [modelFileName];
    if (kScale !== void 0) {
      CurrentKScale = kScale;
    }
    ModelDirSize = ModelDir.length;
  }
  var ModelDirSize = ModelDir.length;
  var BackImageName = "back_class_normal.png";
  var MotionGroupIdle = "Idle";
  var MotionGroupTapBody = "TapBody";
  var HitAreaNameHead = "Head";
  var HitAreaNameBody = "Body";
  var PriorityIdle = 1;
  var PriorityNormal = 2;
  var PriorityForce = 3;
  var MOCConsistencyValidationEnable = true;
  var DebugLogEnable = false;
  var DebugTouchLogEnable = false;
  var CubismLoggingLevel = 0 /* LogLevel_Verbose */;
  var ENABLE_LIMITED_FRAME_RATE = true;
  var LIMITED_FRAME_RATE = 60;

  // .trellis/workspace/lapp-runtime-src/src/renderer/WebSDK/src/lappglmanager.ts
  var canvas = null;
  var gl = null;
  var s_instance = null;
  var LAppGlManager = class _LAppGlManager {
    /**
     * クラスのインスタンス（シングルトン）を返す。
     * インスタンスが生成されていない場合は内部でインスタンスを生成する。
     *
     * @return クラスのインスタンス
     */
    static getInstance() {
      if (s_instance == null) {
        s_instance = new _LAppGlManager();
      }
      return s_instance;
    }
    /**
     * クラスのインスタンス（シングルトン）を解放する。
     */
    static releaseInstance() {
      if (s_instance != null) {
        s_instance.release();
      }
      s_instance = null;
    }
    constructor() {
      canvas = document.getElementById("canvas");
      if (!canvas) {
        console.warn("Canvas element not found during LAppGlManager initialization");
        return;
      }
      gl = canvas.getContext("webgl2");
      if (!gl) {
        alert("Cannot initialize WebGL. This browser does not support.");
        gl = null;
        document.body.innerHTML = "This browser does not support the <code>&lt;canvas&gt;</code> element.";
      }
    }
    /**
     * 解放する。
     */
    release() {
    }
  };

  // .trellis/workspace/lapp-runtime-src/src/renderer/WebSDK/Framework/src/cubismdefaultparameterid.ts
  var CubismDefaultParameterId = Object.freeze({
    // パーツID
    HitAreaPrefix: "HitArea",
    HitAreaHead: "Head",
    HitAreaBody: "Body",
    PartsIdCore: "Parts01Core",
    PartsArmPrefix: "Parts01Arm_",
    PartsArmLPrefix: "Parts01ArmL_",
    PartsArmRPrefix: "Parts01ArmR_",
    // パラメータID
    ParamAngleX: "ParamAngleX",
    ParamAngleY: "ParamAngleY",
    ParamAngleZ: "ParamAngleZ",
    ParamEyeLOpen: "ParamEyeLOpen",
    ParamEyeLSmile: "ParamEyeLSmile",
    ParamEyeROpen: "ParamEyeROpen",
    ParamEyeRSmile: "ParamEyeRSmile",
    ParamEyeBallX: "ParamEyeBallX",
    ParamEyeBallY: "ParamEyeBallY",
    ParamEyeBallForm: "ParamEyeBallForm",
    ParamBrowLY: "ParamBrowLY",
    ParamBrowRY: "ParamBrowRY",
    ParamBrowLX: "ParamBrowLX",
    ParamBrowRX: "ParamBrowRX",
    ParamBrowLAngle: "ParamBrowLAngle",
    ParamBrowRAngle: "ParamBrowRAngle",
    ParamBrowLForm: "ParamBrowLForm",
    ParamBrowRForm: "ParamBrowRForm",
    ParamMouthForm: "ParamMouthForm",
    ParamMouthOpenY: "ParamMouthOpenY",
    ParamCheek: "ParamCheek",
    ParamBodyAngleX: "ParamBodyAngleX",
    ParamBodyAngleY: "ParamBodyAngleY",
    ParamBodyAngleZ: "ParamBodyAngleZ",
    ParamBreath: "ParamBreath",
    ParamArmLA: "ParamArmLA",
    ParamArmRA: "ParamArmRA",
    ParamArmLB: "ParamArmLB",
    ParamArmRB: "ParamArmRB",
    ParamHandL: "ParamHandL",
    ParamHandR: "ParamHandR",
    ParamHairFront: "ParamHairFront",
    ParamHairSide: "ParamHairSide",
    ParamHairBack: "ParamHairBack",
    ParamHairFluffy: "ParamHairFluffy",
    ParamShoulderY: "ParamShoulderY",
    ParamBustX: "ParamBustX",
    ParamBustY: "ParamBustY",
    ParamBaseX: "ParamBaseX",
    ParamBaseY: "ParamBaseY",
    ParamNONE: "NONE:"
  });
  var Live2DCubismFramework12;
  ((Live2DCubismFramework42) => {
    Live2DCubismFramework42.HitAreaBody = CubismDefaultParameterId.HitAreaBody;
    Live2DCubismFramework42.HitAreaHead = CubismDefaultParameterId.HitAreaHead;
    Live2DCubismFramework42.HitAreaPrefix = CubismDefaultParameterId.HitAreaPrefix;
    Live2DCubismFramework42.ParamAngleX = CubismDefaultParameterId.ParamAngleX;
    Live2DCubismFramework42.ParamAngleY = CubismDefaultParameterId.ParamAngleY;
    Live2DCubismFramework42.ParamAngleZ = CubismDefaultParameterId.ParamAngleZ;
    Live2DCubismFramework42.ParamArmLA = CubismDefaultParameterId.ParamArmLA;
    Live2DCubismFramework42.ParamArmLB = CubismDefaultParameterId.ParamArmLB;
    Live2DCubismFramework42.ParamArmRA = CubismDefaultParameterId.ParamArmRA;
    Live2DCubismFramework42.ParamArmRB = CubismDefaultParameterId.ParamArmRB;
    Live2DCubismFramework42.ParamBaseX = CubismDefaultParameterId.ParamBaseX;
    Live2DCubismFramework42.ParamBaseY = CubismDefaultParameterId.ParamBaseY;
    Live2DCubismFramework42.ParamBodyAngleX = CubismDefaultParameterId.ParamBodyAngleX;
    Live2DCubismFramework42.ParamBodyAngleY = CubismDefaultParameterId.ParamBodyAngleY;
    Live2DCubismFramework42.ParamBodyAngleZ = CubismDefaultParameterId.ParamBodyAngleZ;
    Live2DCubismFramework42.ParamBreath = CubismDefaultParameterId.ParamBreath;
    Live2DCubismFramework42.ParamBrowLAngle = CubismDefaultParameterId.ParamBrowLAngle;
    Live2DCubismFramework42.ParamBrowLForm = CubismDefaultParameterId.ParamBrowLForm;
    Live2DCubismFramework42.ParamBrowLX = CubismDefaultParameterId.ParamBrowLX;
    Live2DCubismFramework42.ParamBrowLY = CubismDefaultParameterId.ParamBrowLY;
    Live2DCubismFramework42.ParamBrowRAngle = CubismDefaultParameterId.ParamBrowRAngle;
    Live2DCubismFramework42.ParamBrowRForm = CubismDefaultParameterId.ParamBrowRForm;
    Live2DCubismFramework42.ParamBrowRX = CubismDefaultParameterId.ParamBrowRX;
    Live2DCubismFramework42.ParamBrowRY = CubismDefaultParameterId.ParamBrowRY;
    Live2DCubismFramework42.ParamBustX = CubismDefaultParameterId.ParamBustX;
    Live2DCubismFramework42.ParamBustY = CubismDefaultParameterId.ParamBustY;
    Live2DCubismFramework42.ParamCheek = CubismDefaultParameterId.ParamCheek;
    Live2DCubismFramework42.ParamEyeBallForm = CubismDefaultParameterId.ParamEyeBallForm;
    Live2DCubismFramework42.ParamEyeBallX = CubismDefaultParameterId.ParamEyeBallX;
    Live2DCubismFramework42.ParamEyeBallY = CubismDefaultParameterId.ParamEyeBallY;
    Live2DCubismFramework42.ParamEyeLOpen = CubismDefaultParameterId.ParamEyeLOpen;
    Live2DCubismFramework42.ParamEyeLSmile = CubismDefaultParameterId.ParamEyeLSmile;
    Live2DCubismFramework42.ParamEyeROpen = CubismDefaultParameterId.ParamEyeROpen;
    Live2DCubismFramework42.ParamEyeRSmile = CubismDefaultParameterId.ParamEyeRSmile;
    Live2DCubismFramework42.ParamHairBack = CubismDefaultParameterId.ParamHairBack;
    Live2DCubismFramework42.ParamHairFluffy = CubismDefaultParameterId.ParamHairFluffy;
    Live2DCubismFramework42.ParamHairFront = CubismDefaultParameterId.ParamHairFront;
    Live2DCubismFramework42.ParamHairSide = CubismDefaultParameterId.ParamHairSide;
    Live2DCubismFramework42.ParamHandL = CubismDefaultParameterId.ParamHandL;
    Live2DCubismFramework42.ParamHandR = CubismDefaultParameterId.ParamHandR;
    Live2DCubismFramework42.ParamMouthForm = CubismDefaultParameterId.ParamMouthForm;
    Live2DCubismFramework42.ParamMouthOpenY = CubismDefaultParameterId.ParamMouthOpenY;
    Live2DCubismFramework42.ParamNONE = CubismDefaultParameterId.ParamNONE;
    Live2DCubismFramework42.ParamShoulderY = CubismDefaultParameterId.ParamShoulderY;
    Live2DCubismFramework42.PartsArmLPrefix = CubismDefaultParameterId.PartsArmLPrefix;
    Live2DCubismFramework42.PartsArmPrefix = CubismDefaultParameterId.PartsArmPrefix;
    Live2DCubismFramework42.PartsArmRPrefix = CubismDefaultParameterId.PartsArmRPrefix;
    Live2DCubismFramework42.PartsIdCore = CubismDefaultParameterId.PartsIdCore;
  })(Live2DCubismFramework12 || (Live2DCubismFramework12 = {}));

  // .trellis/workspace/lapp-runtime-src/src/renderer/WebSDK/Framework/src/icubismmodelsetting.ts
  var ICubismModelSetting = class {
  };
  var Live2DCubismFramework13;
  ((Live2DCubismFramework42) => {
    Live2DCubismFramework42.ICubismModelSetting = ICubismModelSetting;
  })(Live2DCubismFramework13 || (Live2DCubismFramework13 = {}));

  // .trellis/workspace/lapp-runtime-src/src/renderer/WebSDK/Framework/src/cubismmodelsettingjson.ts
  var FileReferences = "FileReferences";
  var Groups = "Groups";
  var Layout = "Layout";
  var HitAreas = "HitAreas";
  var Moc = "Moc";
  var Textures = "Textures";
  var Physics = "Physics";
  var Pose = "Pose";
  var Expressions = "Expressions";
  var Motions = "Motions";
  var UserData = "UserData";
  var Name = "Name";
  var FilePath = "File";
  var Id = "Id";
  var Ids = "Ids";
  var SoundPath = "Sound";
  var FadeInTime = "FadeInTime";
  var FadeOutTime = "FadeOutTime";
  var LipSync = "LipSync";
  var EyeBlink = "EyeBlink";
  var CubismModelSettingJson = class extends ICubismModelSetting {
    /**
     * 引数付きコンストラクタ
     *
     * @param buffer    Model3Jsonをバイト配列として読み込んだデータバッファ
     * @param size      Model3Jsonのデータサイズ
     */
    constructor(buffer, size) {
      super();
      __publicField(this, "_json");
      __publicField(this, "_jsonValue");
      this._json = CubismJson.create(buffer, size);
      if (this.getJson()) {
        this._jsonValue = new csmVector();
        this._jsonValue.pushBack(
          this.getJson().getRoot().getValueByString(Groups)
        );
        this._jsonValue.pushBack(
          this.getJson().getRoot().getValueByString(FileReferences).getValueByString(Moc)
        );
        this._jsonValue.pushBack(
          this.getJson().getRoot().getValueByString(FileReferences).getValueByString(Motions)
        );
        this._jsonValue.pushBack(
          this.getJson().getRoot().getValueByString(FileReferences).getValueByString(Expressions)
        );
        this._jsonValue.pushBack(
          this.getJson().getRoot().getValueByString(FileReferences).getValueByString(Textures)
        );
        this._jsonValue.pushBack(
          this.getJson().getRoot().getValueByString(FileReferences).getValueByString(Physics)
        );
        this._jsonValue.pushBack(
          this.getJson().getRoot().getValueByString(FileReferences).getValueByString(Pose)
        );
        this._jsonValue.pushBack(
          this.getJson().getRoot().getValueByString(HitAreas)
        );
      }
    }
    /**
     * デストラクタ相当の処理
     */
    release() {
      CubismJson.delete(this._json);
      this._jsonValue = null;
    }
    /**
     * CubismJsonオブジェクトを取得する
     *
     * @return CubismJson
     */
    getJson() {
      return this._json;
    }
    /**
     * Mocファイルの名前を取得する
     * @return Mocファイルの名前
     */
    getModelFileName() {
      if (!this.isExistModelFile()) {
        return "";
      }
      return this._jsonValue.at(1 /* FrequestNode_Moc */).getRawString();
    }
    /**
     * モデルが使用するテクスチャの数を取得する
     * テクスチャの数
     */
    getTextureCount() {
      if (!this.isExistTextureFiles()) {
        return 0;
      }
      return this._jsonValue.at(4 /* FrequestNode_Textures */).getSize();
    }
    /**
     * テクスチャが配置されたディレクトリの名前を取得する
     * @return テクスチャが配置されたディレクトリの名前
     */
    getTextureDirectory() {
      const texturePath = this._jsonValue.at(4 /* FrequestNode_Textures */).getValueByIndex(0).getRawString();
      const pathArray = texturePath.split("/");
      const arrayLength = pathArray.length - 1;
      let textureDirectoryStr = "";
      for (let i = 0; i < arrayLength; i++) {
        textureDirectoryStr += pathArray[i];
        if (i < arrayLength - 1) {
          textureDirectoryStr += "/";
        }
      }
      return textureDirectoryStr;
    }
    /**
     * モデルが使用するテクスチャの名前を取得する
     * @param index 配列のインデックス値
     * @return テクスチャの名前
     */
    getTextureFileName(index) {
      return this._jsonValue.at(4 /* FrequestNode_Textures */).getValueByIndex(index).getRawString();
    }
    /**
     * モデルに設定された当たり判定の数を取得する
     * @return モデルに設定された当たり判定の数
     */
    getHitAreasCount() {
      if (!this.isExistHitAreas()) {
        return 0;
      }
      return this._jsonValue.at(7 /* FrequestNode_HitAreas */).getSize();
    }
    /**
     * 当たり判定に設定されたIDを取得する
     *
     * @param index 配列のindex
     * @return 当たり判定に設定されたID
     */
    getHitAreaId(index) {
      return CubismFramework.getIdManager().getId(
        this._jsonValue.at(7 /* FrequestNode_HitAreas */).getValueByIndex(index).getValueByString(Id).getRawString()
      );
    }
    /**
     * 当たり判定に設定された名前を取得する
     * @param index 配列のインデックス値
     * @return 当たり判定に設定された名前
     */
    getHitAreaName(index) {
      return this._jsonValue.at(7 /* FrequestNode_HitAreas */).getValueByIndex(index).getValueByString(Name).getRawString();
    }
    /**
     * 物理演算設定ファイルの名前を取得する
     * @return 物理演算設定ファイルの名前
     */
    getPhysicsFileName() {
      if (!this.isExistPhysicsFile()) {
        return "";
      }
      return this._jsonValue.at(5 /* FrequestNode_Physics */).getRawString();
    }
    /**
     * パーツ切り替え設定ファイルの名前を取得する
     * @return パーツ切り替え設定ファイルの名前
     */
    getPoseFileName() {
      if (!this.isExistPoseFile()) {
        return "";
      }
      return this._jsonValue.at(6 /* FrequestNode_Pose */).getRawString();
    }
    /**
     * 表情設定ファイルの数を取得する
     * @return 表情設定ファイルの数
     */
    getExpressionCount() {
      if (!this.isExistExpressionFile()) {
        return 0;
      }
      return this._jsonValue.at(3 /* FrequestNode_Expressions */).getSize();
    }
    /**
     * 表情設定ファイルを識別する名前（別名）を取得する
     * @param index 配列のインデックス値
     * @return 表情の名前
     */
    getExpressionName(index) {
      return this._jsonValue.at(3 /* FrequestNode_Expressions */).getValueByIndex(index).getValueByString(Name).getRawString();
    }
    /**
     * 表情設定ファイルの名前を取得する
     * @param index 配列のインデックス値
     * @return 表情設定ファイルの名前
     */
    getExpressionFileName(index) {
      return this._jsonValue.at(3 /* FrequestNode_Expressions */).getValueByIndex(index).getValueByString(FilePath).getRawString();
    }
    /**
     * モーショングループの数を取得する
     * @return モーショングループの数
     */
    getMotionGroupCount() {
      if (!this.isExistMotionGroups()) {
        return 0;
      }
      return this._jsonValue.at(2 /* FrequestNode_Motions */).getKeys().getSize();
    }
    /**
     * モーショングループの名前を取得する
     * @param index 配列のインデックス値
     * @return モーショングループの名前
     */
    getMotionGroupName(index) {
      if (!this.isExistMotionGroups()) {
        return null;
      }
      return this._jsonValue.at(2 /* FrequestNode_Motions */).getKeys().at(index);
    }
    /**
     * モーショングループに含まれるモーションの数を取得する
     * @param groupName モーショングループの名前
     * @return モーショングループの数
     */
    getMotionCount(groupName) {
      if (!this.isExistMotionGroupName(groupName)) {
        return 0;
      }
      return this._jsonValue.at(2 /* FrequestNode_Motions */).getValueByString(groupName).getSize();
    }
    /**
     * グループ名とインデックス値からモーションファイル名を取得する
     * @param groupName モーショングループの名前
     * @param index     配列のインデックス値
     * @return モーションファイルの名前
     */
    getMotionFileName(groupName, index) {
      if (!this.isExistMotionGroupName(groupName)) {
        return "";
      }
      return this._jsonValue.at(2 /* FrequestNode_Motions */).getValueByString(groupName).getValueByIndex(index).getValueByString(FilePath).getRawString();
    }
    /**
     * モーションに対応するサウンドファイルの名前を取得する
     * @param groupName モーショングループの名前
     * @param index 配列のインデックス値
     * @return サウンドファイルの名前
     */
    getMotionSoundFileName(groupName, index) {
      if (!this.isExistMotionSoundFile(groupName, index)) {
        return "";
      }
      return this._jsonValue.at(2 /* FrequestNode_Motions */).getValueByString(groupName).getValueByIndex(index).getValueByString(SoundPath).getRawString();
    }
    /**
     * モーション開始時のフェードイン処理時間を取得する
     * @param groupName モーショングループの名前
     * @param index 配列のインデックス値
     * @return フェードイン処理時間[秒]
     */
    getMotionFadeInTimeValue(groupName, index) {
      if (!this.isExistMotionFadeIn(groupName, index)) {
        return -1;
      }
      return this._jsonValue.at(2 /* FrequestNode_Motions */).getValueByString(groupName).getValueByIndex(index).getValueByString(FadeInTime).toFloat();
    }
    /**
     * モーション終了時のフェードアウト処理時間を取得する
     * @param groupName モーショングループの名前
     * @param index 配列のインデックス値
     * @return フェードアウト処理時間[秒]
     */
    getMotionFadeOutTimeValue(groupName, index) {
      if (!this.isExistMotionFadeOut(groupName, index)) {
        return -1;
      }
      return this._jsonValue.at(2 /* FrequestNode_Motions */).getValueByString(groupName).getValueByIndex(index).getValueByString(FadeOutTime).toFloat();
    }
    /**
     * ユーザーデータのファイル名を取得する
     * @return ユーザーデータのファイル名
     */
    getUserDataFile() {
      if (!this.isExistUserDataFile()) {
        return "";
      }
      return this.getJson().getRoot().getValueByString(FileReferences).getValueByString(UserData).getRawString();
    }
    /**
     * レイアウト情報を取得する
     * @param outLayoutMap csmMapクラスのインスタンス
     * @return true レイアウト情報が存在する
     * @return false レイアウト情報が存在しない
     */
    getLayoutMap(outLayoutMap) {
      const map = this.getJson().getRoot().getValueByString(Layout).getMap();
      if (map == null) {
        return false;
      }
      let ret = false;
      for (const ite = map.begin(); ite.notEqual(map.end()); ite.preIncrement()) {
        outLayoutMap.setValue(ite.ptr().first, ite.ptr().second.toFloat());
        ret = true;
      }
      return ret;
    }
    /**
     * 目パチに関連付けられたパラメータの数を取得する
     * @return 目パチに関連付けられたパラメータの数
     */
    getEyeBlinkParameterCount() {
      if (!this.isExistEyeBlinkParameters()) {
        return 0;
      }
      let num = 0;
      for (let i = 0; i < this._jsonValue.at(0 /* FrequestNode_Groups */).getSize(); i++) {
        const refI = this._jsonValue.at(0 /* FrequestNode_Groups */).getValueByIndex(i);
        if (refI.isNull() || refI.isError()) {
          continue;
        }
        if (refI.getValueByString(Name).getRawString() == EyeBlink) {
          num = refI.getValueByString(Ids).getVector().getSize();
          break;
        }
      }
      return num;
    }
    /**
     * 目パチに関連付けられたパラメータのIDを取得する
     * @param index 配列のインデックス値
     * @return パラメータID
     */
    getEyeBlinkParameterId(index) {
      if (!this.isExistEyeBlinkParameters()) {
        return null;
      }
      for (let i = 0; i < this._jsonValue.at(0 /* FrequestNode_Groups */).getSize(); i++) {
        const refI = this._jsonValue.at(0 /* FrequestNode_Groups */).getValueByIndex(i);
        if (refI.isNull() || refI.isError()) {
          continue;
        }
        if (refI.getValueByString(Name).getRawString() == EyeBlink) {
          return CubismFramework.getIdManager().getId(
            refI.getValueByString(Ids).getValueByIndex(index).getRawString()
          );
        }
      }
      return null;
    }
    /**
     * リップシンクに関連付けられたパラメータの数を取得する
     * @return リップシンクに関連付けられたパラメータの数
     */
    getLipSyncParameterCount() {
      if (!this.isExistLipSyncParameters()) {
        return 0;
      }
      let num = 0;
      for (let i = 0; i < this._jsonValue.at(0 /* FrequestNode_Groups */).getSize(); i++) {
        const refI = this._jsonValue.at(0 /* FrequestNode_Groups */).getValueByIndex(i);
        if (refI.isNull() || refI.isError()) {
          continue;
        }
        if (refI.getValueByString(Name).getRawString() == LipSync) {
          num = refI.getValueByString(Ids).getVector().getSize();
          break;
        }
      }
      return num;
    }
    /**
     * リップシンクに関連付けられたパラメータの数を取得する
     * @param index 配列のインデックス値
     * @return パラメータID
     */
    getLipSyncParameterId(index) {
      if (!this.isExistLipSyncParameters()) {
        return null;
      }
      for (let i = 0; i < this._jsonValue.at(0 /* FrequestNode_Groups */).getSize(); i++) {
        const refI = this._jsonValue.at(0 /* FrequestNode_Groups */).getValueByIndex(i);
        if (refI.isNull() || refI.isError()) {
          continue;
        }
        if (refI.getValueByString(Name).getRawString() == LipSync) {
          return CubismFramework.getIdManager().getId(
            refI.getValueByString(Ids).getValueByIndex(index).getRawString()
          );
        }
      }
      return null;
    }
    /**
     * モデルファイルのキーが存在するかどうかを確認する
     * @return true キーが存在する
     * @return false キーが存在しない
     */
    isExistModelFile() {
      const node = this._jsonValue.at(1 /* FrequestNode_Moc */);
      return !node.isNull() && !node.isError();
    }
    /**
     * テクスチャファイルのキーが存在するかどうかを確認する
     * @return true キーが存在する
     * @return false キーが存在しない
     */
    isExistTextureFiles() {
      const node = this._jsonValue.at(4 /* FrequestNode_Textures */);
      return !node.isNull() && !node.isError();
    }
    /**
     * 当たり判定のキーが存在するかどうかを確認する
     * @return true キーが存在する
     * @return false キーが存在しない
     */
    isExistHitAreas() {
      const node = this._jsonValue.at(7 /* FrequestNode_HitAreas */);
      return !node.isNull() && !node.isError();
    }
    /**
     * 物理演算ファイルのキーが存在するかどうかを確認する
     * @return true キーが存在する
     * @return false キーが存在しない
     */
    isExistPhysicsFile() {
      const node = this._jsonValue.at(5 /* FrequestNode_Physics */);
      return !node.isNull() && !node.isError();
    }
    /**
     * ポーズ設定ファイルのキーが存在するかどうかを確認する
     * @return true キーが存在する
     * @return false キーが存在しない
     */
    isExistPoseFile() {
      const node = this._jsonValue.at(6 /* FrequestNode_Pose */);
      return !node.isNull() && !node.isError();
    }
    /**
     * 表情設定ファイルのキーが存在するかどうかを確認する
     * @return true キーが存在する
     * @return false キーが存在しない
     */
    isExistExpressionFile() {
      const node = this._jsonValue.at(
        3 /* FrequestNode_Expressions */
      );
      return !node.isNull() && !node.isError();
    }
    /**
     * モーショングループのキーが存在するかどうかを確認する
     * @return true キーが存在する
     * @return false キーが存在しない
     */
    isExistMotionGroups() {
      const node = this._jsonValue.at(2 /* FrequestNode_Motions */);
      return !node.isNull() && !node.isError();
    }
    /**
     * 引数で指定したモーショングループのキーが存在するかどうかを確認する
     * @param groupName  グループ名
     * @return true キーが存在する
     * @return false キーが存在しない
     */
    isExistMotionGroupName(groupName) {
      const node = this._jsonValue.at(2 /* FrequestNode_Motions */).getValueByString(groupName);
      return !node.isNull() && !node.isError();
    }
    /**
     * 引数で指定したモーションに対応するサウンドファイルのキーが存在するかどうかを確認する
     * @param groupName  グループ名
     * @param index 配列のインデックス値
     * @return true キーが存在する
     * @return false キーが存在しない
     */
    isExistMotionSoundFile(groupName, index) {
      const node = this._jsonValue.at(2 /* FrequestNode_Motions */).getValueByString(groupName).getValueByIndex(index).getValueByString(SoundPath);
      return !node.isNull() && !node.isError();
    }
    /**
     * 引数で指定したモーションに対応するフェードイン時間のキーが存在するかどうかを確認する
     * @param groupName  グループ名
     * @param index 配列のインデックス値
     * @return true キーが存在する
     * @return false キーが存在しない
     */
    isExistMotionFadeIn(groupName, index) {
      const node = this._jsonValue.at(2 /* FrequestNode_Motions */).getValueByString(groupName).getValueByIndex(index).getValueByString(FadeInTime);
      return !node.isNull() && !node.isError();
    }
    /**
     * 引数で指定したモーションに対応するフェードアウト時間のキーが存在するかどうかを確認する
     * @param groupName  グループ名
     * @param index 配列のインデックス値
     * @return true キーが存在する
     * @return false キーが存在しない
     */
    isExistMotionFadeOut(groupName, index) {
      const node = this._jsonValue.at(2 /* FrequestNode_Motions */).getValueByString(groupName).getValueByIndex(index).getValueByString(FadeOutTime);
      return !node.isNull() && !node.isError();
    }
    /**
     * UserDataのファイル名が存在するかどうかを確認する
     * @return true キーが存在する
     * @return false キーが存在しない
     */
    isExistUserDataFile() {
      const node = this.getJson().getRoot().getValueByString(FileReferences).getValueByString(UserData);
      return !node.isNull() && !node.isError();
    }
    /**
     * 目ぱちに対応付けられたパラメータが存在するかどうかを確認する
     * @return true キーが存在する
     * @return false キーが存在しない
     */
    isExistEyeBlinkParameters() {
      if (this._jsonValue.at(0 /* FrequestNode_Groups */).isNull() || this._jsonValue.at(0 /* FrequestNode_Groups */).isError()) {
        return false;
      }
      for (let i = 0; i < this._jsonValue.at(0 /* FrequestNode_Groups */).getSize(); ++i) {
        if (this._jsonValue.at(0 /* FrequestNode_Groups */).getValueByIndex(i).getValueByString(Name).getRawString() == EyeBlink) {
          return true;
        }
      }
      return false;
    }
    /**
     * リップシンクに対応付けられたパラメータが存在するかどうかを確認する
     * @return true キーが存在する
     * @return false キーが存在しない
     */
    isExistLipSyncParameters() {
      if (this._jsonValue.at(0 /* FrequestNode_Groups */).isNull() || this._jsonValue.at(0 /* FrequestNode_Groups */).isError()) {
        return false;
      }
      for (let i = 0; i < this._jsonValue.at(0 /* FrequestNode_Groups */).getSize(); ++i) {
        if (this._jsonValue.at(0 /* FrequestNode_Groups */).getValueByIndex(i).getValueByString(Name).getRawString() == LipSync) {
          return true;
        }
      }
      return false;
    }
  };
  var Live2DCubismFramework14;
  ((Live2DCubismFramework42) => {
    Live2DCubismFramework42.CubismModelSettingJson = CubismModelSettingJson;
  })(Live2DCubismFramework14 || (Live2DCubismFramework14 = {}));

  // .trellis/workspace/lapp-runtime-src/src/renderer/WebSDK/Framework/src/effect/cubismbreath.ts
  var CubismBreath = class _CubismBreath {
    /**
     * コンストラクタ
     */
    constructor() {
      __publicField(this, "_breathParameters");
      // 呼吸にひもづいているパラメータのリスト
      __publicField(this, "_currentTime");
      this._currentTime = 0;
    }
    /**
     * インスタンスの作成
     */
    static create() {
      return new _CubismBreath();
    }
    /**
     * インスタンスの破棄
     * @param instance 対象のCubismBreath
     */
    static delete(instance) {
      if (instance != null) {
        instance = null;
      }
    }
    /**
     * 呼吸のパラメータの紐づけ
     * @param breathParameters 呼吸を紐づけたいパラメータのリスト
     */
    setParameters(breathParameters) {
      this._breathParameters = breathParameters;
    }
    /**
     * 呼吸に紐づいているパラメータの取得
     * @return 呼吸に紐づいているパラメータのリスト
     */
    getParameters() {
      return this._breathParameters;
    }
    /**
     * モデルのパラメータの更新
     * @param model 対象のモデル
     * @param deltaTimeSeconds デルタ時間[秒]
     */
    updateParameters(model, deltaTimeSeconds) {
      this._currentTime += deltaTimeSeconds;
      const t = this._currentTime * 2 * 3.14159;
      for (let i = 0; i < this._breathParameters.getSize(); ++i) {
        const data = this._breathParameters.at(i);
        model.addParameterValueById(
          data.parameterId,
          data.offset + data.peak * Math.sin(t / data.cycle),
          data.weight
        );
      }
    }
    // 積算時間[秒]
  };
  var BreathParameterData = class {
    /**
     * コンストラクタ
     * @param parameterId   呼吸をひもづけるパラメータID
     * @param offset        呼吸を正弦波としたときの、波のオフセット
     * @param peak          呼吸を正弦波としたときの、波の高さ
     * @param cycle         呼吸を正弦波としたときの、波の周期
     * @param weight        パラメータへの重み
     */
    constructor(parameterId, offset, peak, cycle, weight) {
      __publicField(this, "parameterId");
      // 呼吸をひもづけるパラメータID\
      __publicField(this, "offset");
      // 呼吸を正弦波としたときの、波のオフセット
      __publicField(this, "peak");
      // 呼吸を正弦波としたときの、波の高さ
      __publicField(this, "cycle");
      // 呼吸を正弦波としたときの、波の周期
      __publicField(this, "weight");
      this.parameterId = parameterId == void 0 ? null : parameterId;
      this.offset = offset == void 0 ? 0 : offset;
      this.peak = peak == void 0 ? 0 : peak;
      this.cycle = cycle == void 0 ? 0 : cycle;
      this.weight = weight == void 0 ? 0 : weight;
    }
    // パラメータへの重み
  };
  var Live2DCubismFramework15;
  ((Live2DCubismFramework42) => {
    Live2DCubismFramework42.BreathParameterData = BreathParameterData;
    Live2DCubismFramework42.CubismBreath = CubismBreath;
  })(Live2DCubismFramework15 || (Live2DCubismFramework15 = {}));

  // .trellis/workspace/lapp-runtime-src/src/renderer/WebSDK/Framework/src/effect/cubismeyeblink.ts
  var _CubismEyeBlink = class _CubismEyeBlink {
    /**
     * コンストラクタ
     * @param modelSetting モデルの設定情報
     */
    constructor(modelSetting) {
      __publicField(this, "_blinkingState");
      // 現在の状態
      __publicField(this, "_parameterIds");
      // 操作対象のパラメータのIDのリスト
      __publicField(this, "_nextBlinkingTime");
      // 次のまばたきの時刻[秒]
      __publicField(this, "_stateStartTimeSeconds");
      // 現在の状態が開始した時刻[秒]
      __publicField(this, "_blinkingIntervalSeconds");
      // まばたきの間隔[秒]
      __publicField(this, "_closingSeconds");
      // まぶたを閉じる動作の所要時間[秒]
      __publicField(this, "_closedSeconds");
      // まぶたを閉じている動作の所要時間[秒]
      __publicField(this, "_openingSeconds");
      // まぶたを開く動作の所要時間[秒]
      __publicField(this, "_userTimeSeconds");
      this._blinkingState = 0 /* EyeState_First */;
      this._nextBlinkingTime = 0;
      this._stateStartTimeSeconds = 0;
      this._blinkingIntervalSeconds = 4;
      this._closingSeconds = 0.1;
      this._closedSeconds = 0.05;
      this._openingSeconds = 0.15;
      this._userTimeSeconds = 0;
      this._parameterIds = new csmVector();
      if (modelSetting == null) {
        return;
      }
      for (let i = 0; i < modelSetting.getEyeBlinkParameterCount(); ++i) {
        this._parameterIds.pushBack(modelSetting.getEyeBlinkParameterId(i));
      }
    }
    /**
     * インスタンスを作成する
     * @param modelSetting モデルの設定情報
     * @return 作成されたインスタンス
     * @note 引数がNULLの場合、パラメータIDが設定されていない空のインスタンスを作成する。
     */
    static create(modelSetting = null) {
      return new _CubismEyeBlink(modelSetting);
    }
    /**
     * インスタンスの破棄
     * @param eyeBlink 対象のCubismEyeBlink
     */
    static delete(eyeBlink) {
      if (eyeBlink != null) {
        eyeBlink = null;
      }
    }
    /**
     * まばたきの間隔の設定
     * @param blinkingInterval まばたきの間隔の時間[秒]
     */
    setBlinkingInterval(blinkingInterval) {
      this._blinkingIntervalSeconds = blinkingInterval;
    }
    /**
     * まばたきのモーションの詳細設定
     * @param closing   まぶたを閉じる動作の所要時間[秒]
     * @param closed    まぶたを閉じている動作の所要時間[秒]
     * @param opening   まぶたを開く動作の所要時間[秒]
     */
    setBlinkingSetting(closing, closed, opening) {
      this._closingSeconds = closing;
      this._closedSeconds = closed;
      this._openingSeconds = opening;
    }
    /**
     * まばたきさせるパラメータIDのリストの設定
     * @param parameterIds パラメータのIDのリスト
     */
    setParameterIds(parameterIds) {
      this._parameterIds = parameterIds;
    }
    /**
     * まばたきさせるパラメータIDのリストの取得
     * @return パラメータIDのリスト
     */
    getParameterIds() {
      return this._parameterIds;
    }
    /**
     * モデルのパラメータの更新
     * @param model 対象のモデル
     * @param deltaTimeSeconds デルタ時間[秒]
     */
    updateParameters(model, deltaTimeSeconds) {
      this._userTimeSeconds += deltaTimeSeconds;
      let parameterValue;
      let t = 0;
      const blinkingState = this._blinkingState;
      switch (blinkingState) {
        case 2 /* EyeState_Closing */:
          t = (this._userTimeSeconds - this._stateStartTimeSeconds) / this._closingSeconds;
          if (t >= 1) {
            t = 1;
            this._blinkingState = 3 /* EyeState_Closed */;
            this._stateStartTimeSeconds = this._userTimeSeconds;
          }
          parameterValue = 1 - t;
          break;
        case 3 /* EyeState_Closed */:
          t = (this._userTimeSeconds - this._stateStartTimeSeconds) / this._closedSeconds;
          if (t >= 1) {
            this._blinkingState = 4 /* EyeState_Opening */;
            this._stateStartTimeSeconds = this._userTimeSeconds;
          }
          parameterValue = 0;
          break;
        case 4 /* EyeState_Opening */:
          t = (this._userTimeSeconds - this._stateStartTimeSeconds) / this._openingSeconds;
          if (t >= 1) {
            t = 1;
            this._blinkingState = 1 /* EyeState_Interval */;
            this._nextBlinkingTime = this.determinNextBlinkingTiming();
          }
          parameterValue = t;
          break;
        case 1 /* EyeState_Interval */:
          if (this._nextBlinkingTime < this._userTimeSeconds) {
            this._blinkingState = 2 /* EyeState_Closing */;
            this._stateStartTimeSeconds = this._userTimeSeconds;
          }
          parameterValue = 1;
          break;
        case 0 /* EyeState_First */:
        default:
          this._blinkingState = 1 /* EyeState_Interval */;
          this._nextBlinkingTime = this.determinNextBlinkingTiming();
          parameterValue = 1;
          break;
      }
      if (!_CubismEyeBlink.CloseIfZero) {
        parameterValue = -parameterValue;
      }
      for (let i = 0; i < this._parameterIds.getSize(); ++i) {
        model.setParameterValueById(this._parameterIds.at(i), parameterValue);
      }
    }
    /**
     * 次の瞬きのタイミングの決定
     *
     * @return 次のまばたきを行う時刻[秒]
     */
    determinNextBlinkingTiming() {
      const r = Math.random();
      return this._userTimeSeconds + r * (2 * this._blinkingIntervalSeconds - 1);
    }
  };
  // デルタ時間の積算値[秒]
  /**
   * IDで指定された目のパラメータが、0のときに閉じるなら true 、1の時に閉じるなら false 。
   */
  __publicField(_CubismEyeBlink, "CloseIfZero", true);
  var CubismEyeBlink = _CubismEyeBlink;
  var EyeState = /* @__PURE__ */ ((EyeState2) => {
    EyeState2[EyeState2["EyeState_First"] = 0] = "EyeState_First";
    EyeState2[EyeState2["EyeState_Interval"] = 1] = "EyeState_Interval";
    EyeState2[EyeState2["EyeState_Closing"] = 2] = "EyeState_Closing";
    EyeState2[EyeState2["EyeState_Closed"] = 3] = "EyeState_Closed";
    EyeState2[EyeState2["EyeState_Opening"] = 4] = "EyeState_Opening";
    return EyeState2;
  })(EyeState || {});
  var Live2DCubismFramework16;
  ((Live2DCubismFramework42) => {
    Live2DCubismFramework42.CubismEyeBlink = CubismEyeBlink;
    Live2DCubismFramework42.EyeState = EyeState;
  })(Live2DCubismFramework16 || (Live2DCubismFramework16 = {}));

  // .trellis/workspace/lapp-runtime-src/src/renderer/WebSDK/Framework/src/effect/cubismpose.ts
  var Epsilon = 1e-3;
  var DefaultFadeInSeconds = 0.5;
  var FadeIn = "FadeInTime";
  var Link = "Link";
  var Groups2 = "Groups";
  var Id2 = "Id";
  var CubismPose = class _CubismPose {
    /**
     * コンストラクタ
     */
    constructor() {
      __publicField(this, "_partGroups");
      // パーツグループ
      __publicField(this, "_partGroupCounts");
      // それぞれのパーツグループの個数
      __publicField(this, "_fadeTimeSeconds");
      // フェード時間[秒]
      __publicField(this, "_lastModel");
      this._fadeTimeSeconds = DefaultFadeInSeconds;
      this._lastModel = null;
      this._partGroups = new csmVector();
      this._partGroupCounts = new csmVector();
    }
    /**
     * インスタンスの作成
     * @param pose3json pose3.jsonのデータ
     * @param size pose3.jsonのデータのサイズ[byte]
     * @return 作成されたインスタンス
     */
    static create(pose3json, size) {
      const json = CubismJson.create(pose3json, size);
      if (!json) {
        return null;
      }
      const ret = new _CubismPose();
      const root = json.getRoot();
      if (!root.getValueByString(FadeIn).isNull()) {
        ret._fadeTimeSeconds = root.getValueByString(FadeIn).toFloat(DefaultFadeInSeconds);
        if (ret._fadeTimeSeconds <= 0) {
          ret._fadeTimeSeconds = DefaultFadeInSeconds;
        }
      }
      const poseListInfo = root.getValueByString(Groups2);
      const poseCount = poseListInfo.getSize();
      for (let poseIndex = 0; poseIndex < poseCount; ++poseIndex) {
        const idListInfo = poseListInfo.getValueByIndex(poseIndex);
        const idCount = idListInfo.getSize();
        let groupCount = 0;
        for (let groupIndex = 0; groupIndex < idCount; ++groupIndex) {
          const partInfo = idListInfo.getValueByIndex(groupIndex);
          const partData = new PartData();
          const parameterId = CubismFramework.getIdManager().getId(
            partInfo.getValueByString(Id2).getRawString()
          );
          partData.partId = parameterId;
          if (!partInfo.getValueByString(Link).isNull()) {
            const linkListInfo = partInfo.getValueByString(Link);
            const linkCount = linkListInfo.getSize();
            for (let linkIndex = 0; linkIndex < linkCount; ++linkIndex) {
              const linkPart = new PartData();
              const linkId = CubismFramework.getIdManager().getId(
                linkListInfo.getValueByIndex(linkIndex).getString()
              );
              linkPart.partId = linkId;
              partData.link.pushBack(linkPart);
            }
          }
          ret._partGroups.pushBack(partData.clone());
          ++groupCount;
        }
        ret._partGroupCounts.pushBack(groupCount);
      }
      CubismJson.delete(json);
      return ret;
    }
    /**
     * インスタンスを破棄する
     * @param pose 対象のCubismPose
     */
    static delete(pose) {
      if (pose != null) {
        pose = null;
      }
    }
    /**
     * モデルのパラメータの更新
     * @param model 対象のモデル
     * @param deltaTimeSeconds デルタ時間[秒]
     */
    updateParameters(model, deltaTimeSeconds) {
      if (model != this._lastModel) {
        this.reset(model);
      }
      this._lastModel = model;
      if (deltaTimeSeconds < 0) {
        deltaTimeSeconds = 0;
      }
      let beginIndex = 0;
      for (let i = 0; i < this._partGroupCounts.getSize(); i++) {
        const partGroupCount = this._partGroupCounts.at(i);
        this.doFade(model, deltaTimeSeconds, beginIndex, partGroupCount);
        beginIndex += partGroupCount;
      }
      this.copyPartOpacities(model);
    }
    /**
     * 表示を初期化
     * @param model 対象のモデル
     * @note 不透明度の初期値が0でないパラメータは、不透明度を１に設定する
     */
    reset(model) {
      let beginIndex = 0;
      for (let i = 0; i < this._partGroupCounts.getSize(); ++i) {
        const groupCount = this._partGroupCounts.at(i);
        for (let j = beginIndex; j < beginIndex + groupCount; ++j) {
          this._partGroups.at(j).initialize(model);
          const partsIndex = this._partGroups.at(j).partIndex;
          const paramIndex = this._partGroups.at(j).parameterIndex;
          if (partsIndex < 0) {
            continue;
          }
          model.setPartOpacityByIndex(partsIndex, j == beginIndex ? 1 : 0);
          model.setParameterValueByIndex(paramIndex, j == beginIndex ? 1 : 0);
          for (let k = 0; k < this._partGroups.at(j).link.getSize(); ++k) {
            this._partGroups.at(j).link.at(k).initialize(model);
          }
        }
        beginIndex += groupCount;
      }
    }
    /**
     * パーツの不透明度をコピー
     *
     * @param model 対象のモデル
     */
    copyPartOpacities(model) {
      for (let groupIndex = 0; groupIndex < this._partGroups.getSize(); ++groupIndex) {
        const partData = this._partGroups.at(groupIndex);
        if (partData.link.getSize() == 0) {
          continue;
        }
        const partIndex = this._partGroups.at(groupIndex).partIndex;
        const opacity = model.getPartOpacityByIndex(partIndex);
        for (let linkIndex = 0; linkIndex < partData.link.getSize(); ++linkIndex) {
          const linkPart = partData.link.at(linkIndex);
          const linkPartIndex = linkPart.partIndex;
          if (linkPartIndex < 0) {
            continue;
          }
          model.setPartOpacityByIndex(linkPartIndex, opacity);
        }
      }
    }
    /**
     * パーツのフェード操作を行う。
     * @param model 対象のモデル
     * @param deltaTimeSeconds デルタ時間[秒]
     * @param beginIndex フェード操作を行うパーツグループの先頭インデックス
     * @param partGroupCount フェード操作を行うパーツグループの個数
     */
    doFade(model, deltaTimeSeconds, beginIndex, partGroupCount) {
      let visiblePartIndex = -1;
      let newOpacity = 1;
      const phi = 0.5;
      const backOpacityThreshold = 0.15;
      for (let i = beginIndex; i < beginIndex + partGroupCount; ++i) {
        const partIndex = this._partGroups.at(i).partIndex;
        const paramIndex = this._partGroups.at(i).parameterIndex;
        if (model.getParameterValueByIndex(paramIndex) > Epsilon) {
          if (visiblePartIndex >= 0) {
            break;
          }
          visiblePartIndex = i;
          newOpacity = model.getPartOpacityByIndex(partIndex);
          newOpacity += deltaTimeSeconds / this._fadeTimeSeconds;
          if (newOpacity > 1) {
            newOpacity = 1;
          }
        }
      }
      if (visiblePartIndex < 0) {
        visiblePartIndex = 0;
        newOpacity = 1;
      }
      for (let i = beginIndex; i < beginIndex + partGroupCount; ++i) {
        const partsIndex = this._partGroups.at(i).partIndex;
        if (visiblePartIndex == i) {
          model.setPartOpacityByIndex(partsIndex, newOpacity);
        } else {
          let opacity = model.getPartOpacityByIndex(partsIndex);
          let a1;
          if (newOpacity < phi) {
            a1 = newOpacity * (phi - 1) / phi + 1;
          } else {
            a1 = (1 - newOpacity) * phi / (1 - phi);
          }
          const backOpacity = (1 - a1) * (1 - newOpacity);
          if (backOpacity > backOpacityThreshold) {
            a1 = 1 - backOpacityThreshold / (1 - newOpacity);
          }
          if (opacity > a1) {
            opacity = a1;
          }
          model.setPartOpacityByIndex(partsIndex, opacity);
        }
      }
    }
    // 前回操作したモデル
  };
  var PartData = class _PartData {
    /**
     * コンストラクタ
     */
    constructor(v) {
      __publicField(this, "partId");
      // パーツID
      __publicField(this, "parameterIndex");
      // パラメータのインデックス
      __publicField(this, "partIndex");
      // パーツのインデックス
      __publicField(this, "link");
      this.parameterIndex = 0;
      this.partIndex = 0;
      this.link = new csmVector();
      if (v != void 0) {
        this.partId = v.partId;
        for (const ite = v.link.begin(); ite.notEqual(v.link.end()); ite.preIncrement()) {
          this.link.pushBack(ite.ptr().clone());
        }
      }
    }
    /**
     * =演算子のオーバーロード
     */
    assignment(v) {
      this.partId = v.partId;
      for (const ite = v.link.begin(); ite.notEqual(v.link.end()); ite.preIncrement()) {
        this.link.pushBack(ite.ptr().clone());
      }
      return this;
    }
    /**
     * 初期化
     * @param model 初期化に使用するモデル
     */
    initialize(model) {
      this.parameterIndex = model.getParameterIndex(this.partId);
      this.partIndex = model.getPartIndex(this.partId);
      model.setParameterValueByIndex(this.parameterIndex, 1);
    }
    /**
     * オブジェクトのコピーを生成する
     */
    clone() {
      const clonePartData = new _PartData();
      clonePartData.partId = this.partId;
      clonePartData.parameterIndex = this.parameterIndex;
      clonePartData.partIndex = this.partIndex;
      clonePartData.link = new csmVector();
      for (let ite = this.link.begin(); ite.notEqual(this.link.end()); ite.increment()) {
        clonePartData.link.pushBack(ite.ptr().clone());
      }
      return clonePartData;
    }
    // 連動するパラメータ
  };
  var Live2DCubismFramework17;
  ((Live2DCubismFramework42) => {
    Live2DCubismFramework42.CubismPose = CubismPose;
    Live2DCubismFramework42.PartData = PartData;
  })(Live2DCubismFramework17 || (Live2DCubismFramework17 = {}));

  // .trellis/workspace/lapp-runtime-src/src/renderer/WebSDK/Framework/src/math/cubismmodelmatrix.ts
  var CubismModelMatrix = class extends CubismMatrix44 {
    /**
     * コンストラクタ
     *
     * @param w 横幅
     * @param h 縦幅
     */
    constructor(w, h) {
      super();
      __publicField(this, "_width");
      // 横幅
      __publicField(this, "_height");
      this._width = w !== void 0 ? w : 0;
      this._height = h !== void 0 ? h : 0;
      this.setHeight(2);
    }
    /**
     * 横幅を設定
     *
     * @param w 横幅
     */
    setWidth(w) {
      const scaleX = w / this._width;
      const scaleY = scaleX;
      this.scale(scaleX, scaleY);
    }
    /**
     * 縦幅を設定
     * @param h 縦幅
     */
    setHeight(h) {
      const scaleX = h / this._height;
      const scaleY = scaleX;
      this.scale(scaleX, scaleY);
    }
    /**
     * 位置を設定
     *
     * @param x X軸の位置
     * @param y Y軸の位置
     */
    setPosition(x, y) {
      this.translate(x, y);
    }
    /**
     * 中心位置を設定
     *
     * @param x X軸の中心位置
     * @param y Y軸の中心位置
     *
     * @note widthかheightを設定したあとでないと、拡大率が正しく取得できないためずれる。
     */
    setCenterPosition(x, y) {
      this.centerX(x);
      this.centerY(y);
    }
    /**
     * 上辺の位置を設定する
     *
     * @param y 上辺のY軸位置
     */
    top(y) {
      this.setY(y);
    }
    /**
     * 下辺の位置を設定する
     *
     * @param y 下辺のY軸位置
     */
    bottom(y) {
      const h = this._height * this.getScaleY();
      this.translateY(y - h);
    }
    /**
     * 左辺の位置を設定
     *
     * @param x 左辺のX軸位置
     */
    left(x) {
      this.setX(x);
    }
    /**
     * 右辺の位置を設定
     *
     * @param x 右辺のX軸位置
     */
    right(x) {
      const w = this._width * this.getScaleX();
      this.translateX(x - w);
    }
    /**
     * X軸の中心位置を設定
     *
     * @param x X軸の中心位置
     */
    centerX(x) {
      const w = this._width * this.getScaleX();
      this.translateX(x - w / 2);
    }
    /**
     * X軸の位置を設定
     *
     * @param x X軸の位置
     */
    setX(x) {
      this.translateX(x);
    }
    /**
     * Y軸の中心位置を設定
     *
     * @param y Y軸の中心位置
     */
    centerY(y) {
      const h = this._height * this.getScaleY();
      this.translateY(y - h / 2);
    }
    /**
     * Y軸の位置を設定する
     *
     * @param y Y軸の位置
     */
    setY(y) {
      this.translateY(y);
    }
    /**
     * レイアウト情報から位置を設定
     *
     * @param layout レイアウト情報
     */
    setupFromLayout(layout) {
      const keyWidth = "width";
      const keyHeight = "height";
      const keyX = "x";
      const keyY = "y";
      const keyCenterX = "center_x";
      const keyCenterY = "center_y";
      const keyTop = "top";
      const keyBottom = "bottom";
      const keyLeft = "left";
      const keyRight = "right";
      for (const ite = layout.begin(); ite.notEqual(layout.end()); ite.preIncrement()) {
        const key = ite.ptr().first;
        const value = ite.ptr().second;
        if (key == keyWidth) {
          this.setWidth(value);
        } else if (key == keyHeight) {
          this.setHeight(value);
        }
      }
      for (const ite = layout.begin(); ite.notEqual(layout.end()); ite.preIncrement()) {
        const key = ite.ptr().first;
        const value = ite.ptr().second;
        if (key == keyX) {
          this.setX(value);
        } else if (key == keyY) {
          this.setY(value);
        } else if (key == keyCenterX) {
          this.centerX(value);
        } else if (key == keyCenterY) {
          this.centerY(value);
        } else if (key == keyTop) {
          this.top(value);
        } else if (key == keyBottom) {
          this.bottom(value);
        } else if (key == keyLeft) {
          this.left(value);
        } else if (key == keyRight) {
          this.right(value);
        }
      }
    }
    // 縦幅
  };
  var Live2DCubismFramework18;
  ((Live2DCubismFramework42) => {
    Live2DCubismFramework42.CubismModelMatrix = CubismModelMatrix;
  })(Live2DCubismFramework18 || (Live2DCubismFramework18 = {}));

  // .trellis/workspace/lapp-runtime-src/src/renderer/WebSDK/Framework/src/math/cubismvector2.ts
  var CubismVector2 = class _CubismVector2 {
    /**
     * コンストラクタ
     */
    constructor(x, y) {
      this.x = x;
      this.y = y;
      this.x = x == void 0 ? 0 : x;
      this.y = y == void 0 ? 0 : y;
    }
    /**
     * ベクトルの加算
     *
     * @param vector2 加算するベクトル値
     * @return 加算結果 ベクトル値
     */
    add(vector2) {
      const ret = new _CubismVector2(0, 0);
      ret.x = this.x + vector2.x;
      ret.y = this.y + vector2.y;
      return ret;
    }
    /**
     * ベクトルの減算
     *
     * @param vector2 減算するベクトル値
     * @return 減算結果 ベクトル値
     */
    substract(vector2) {
      const ret = new _CubismVector2(0, 0);
      ret.x = this.x - vector2.x;
      ret.y = this.y - vector2.y;
      return ret;
    }
    /**
     * ベクトルの乗算
     *
     * @param vector2 乗算するベクトル値
     * @return 乗算結果 ベクトル値
     */
    multiply(vector2) {
      const ret = new _CubismVector2(0, 0);
      ret.x = this.x * vector2.x;
      ret.y = this.y * vector2.y;
      return ret;
    }
    /**
     * ベクトルの乗算(スカラー)
     *
     * @param scalar 乗算するスカラー値
     * @return 乗算結果 ベクトル値
     */
    multiplyByScaler(scalar) {
      return this.multiply(new _CubismVector2(scalar, scalar));
    }
    /**
     * ベクトルの除算
     *
     * @param vector2 除算するベクトル値
     * @return 除算結果 ベクトル値
     */
    division(vector2) {
      const ret = new _CubismVector2(0, 0);
      ret.x = this.x / vector2.x;
      ret.y = this.y / vector2.y;
      return ret;
    }
    /**
     * ベクトルの除算(スカラー)
     *
     * @param scalar 除算するスカラー値
     * @return 除算結果 ベクトル値
     */
    divisionByScalar(scalar) {
      return this.division(new _CubismVector2(scalar, scalar));
    }
    /**
     * ベクトルの長さを取得する
     *
     * @return ベクトルの長さ
     */
    getLength() {
      return Math.sqrt(this.x * this.x + this.y * this.y);
    }
    /**
     * ベクトルの距離の取得
     *
     * @param a 点
     * @return ベクトルの距離
     */
    getDistanceWith(a) {
      return Math.sqrt(
        (this.x - a.x) * (this.x - a.x) + (this.y - a.y) * (this.y - a.y)
      );
    }
    /**
     * ドット積の計算
     *
     * @param a 値
     * @return 結果
     */
    dot(a) {
      return this.x * a.x + this.y * a.y;
    }
    /**
     * 正規化の適用
     */
    normalize() {
      const length = Math.pow(this.x * this.x + this.y * this.y, 0.5);
      this.x = this.x / length;
      this.y = this.y / length;
    }
    /**
     * 等しさの確認（等しいか？）
     *
     * 値が等しいか？
     *
     * @param rhs 確認する値
     * @return true 値は等しい
     * @return false 値は等しくない
     */
    isEqual(rhs) {
      return this.x == rhs.x && this.y == rhs.y;
    }
    /**
     * 等しさの確認（等しくないか？）
     *
     * 値が等しくないか？
     *
     * @param rhs 確認する値
     * @return true 値は等しくない
     * @return false 値は等しい
     */
    isNotEqual(rhs) {
      return !this.isEqual(rhs);
    }
  };
  var Live2DCubismFramework19;
  ((Live2DCubismFramework42) => {
    Live2DCubismFramework42.CubismVector2 = CubismVector2;
  })(Live2DCubismFramework19 || (Live2DCubismFramework19 = {}));

  // .trellis/workspace/lapp-runtime-src/src/renderer/WebSDK/Framework/src/math/cubismmath.ts
  var _CubismMath = class _CubismMath {
    /**
     * 第一引数の値を最小値と最大値の範囲に収めた値を返す
     *
     * @param value 収められる値
     * @param min   範囲の最小値
     * @param max   範囲の最大値
     * @return 最小値と最大値の範囲に収めた値
     */
    static range(value, min, max) {
      if (value < min) {
        value = min;
      } else if (value > max) {
        value = max;
      }
      return value;
    }
    /**
     * サイン関数の値を求める
     *
     * @param x 角度値（ラジアン）
     * @return サイン関数sin(x)の値
     */
    static sin(x) {
      return Math.sin(x);
    }
    /**
     * コサイン関数の値を求める
     *
     * @param x 角度値(ラジアン)
     * @return コサイン関数cos(x)の値
     */
    static cos(x) {
      return Math.cos(x);
    }
    /**
     * 値の絶対値を求める
     *
     * @param x 絶対値を求める値
     * @return 値の絶対値
     */
    static abs(x) {
      return Math.abs(x);
    }
    /**
     * 平方根(ルート)を求める
     * @param x -> 平方根を求める値
     * @return 値の平方根
     */
    static sqrt(x) {
      return Math.sqrt(x);
    }
    /**
     * 立方根を求める
     * @param x -> 立方根を求める値
     * @return 値の立方根
     */
    static cbrt(x) {
      if (x === 0) {
        return x;
      }
      let cx = x;
      const isNegativeNumber = cx < 0;
      if (isNegativeNumber) {
        cx = -cx;
      }
      let ret;
      if (cx === Infinity) {
        ret = Infinity;
      } else {
        ret = Math.exp(Math.log(cx) / 3);
        ret = (cx / (ret * ret) + 2 * ret) / 3;
      }
      return isNegativeNumber ? -ret : ret;
    }
    /**
     * イージング処理されたサインを求める
     * フェードイン・アウト時のイージングに利用できる
     *
     * @param value イージングを行う値
     * @return イージング処理されたサイン値
     */
    static getEasingSine(value) {
      if (value < 0) {
        return 0;
      } else if (value > 1) {
        return 1;
      }
      return 0.5 - 0.5 * this.cos(value * Math.PI);
    }
    /**
     * 大きい方の値を返す
     *
     * @param left 左辺の値
     * @param right 右辺の値
     * @return 大きい方の値
     */
    static max(left, right) {
      return left > right ? left : right;
    }
    /**
     * 小さい方の値を返す
     *
     * @param left  左辺の値
     * @param right 右辺の値
     * @return 小さい方の値
     */
    static min(left, right) {
      return left > right ? right : left;
    }
    /**
     * 角度値をラジアン値に変換する
     *
     * @param degrees   角度値
     * @return 角度値から変換したラジアン値
     */
    static degreesToRadian(degrees) {
      return degrees / 180 * Math.PI;
    }
    /**
     * ラジアン値を角度値に変換する
     *
     * @param radian    ラジアン値
     * @return ラジアン値から変換した角度値
     */
    static radianToDegrees(radian) {
      return radian * 180 / Math.PI;
    }
    /**
     * ２つのベクトルからラジアン値を求める
     *
     * @param from  始点ベクトル
     * @param to    終点ベクトル
     * @return ラジアン値から求めた方向ベクトル
     */
    static directionToRadian(from, to) {
      const q1 = Math.atan2(to.y, to.x);
      const q2 = Math.atan2(from.y, from.x);
      let ret = q1 - q2;
      while (ret < -Math.PI) {
        ret += Math.PI * 2;
      }
      while (ret > Math.PI) {
        ret -= Math.PI * 2;
      }
      return ret;
    }
    /**
     * ２つのベクトルから角度値を求める
     *
     * @param from  始点ベクトル
     * @param to    終点ベクトル
     * @return 角度値から求めた方向ベクトル
     */
    static directionToDegrees(from, to) {
      const radian = this.directionToRadian(from, to);
      let degree = this.radianToDegrees(radian);
      if (to.x - from.x > 0) {
        degree = -degree;
      }
      return degree;
    }
    /**
     * ラジアン値を方向ベクトルに変換する。
     *
     * @param totalAngle    ラジアン値
     * @return ラジアン値から変換した方向ベクトル
     */
    static radianToDirection(totalAngle) {
      const ret = new CubismVector2();
      ret.x = this.sin(totalAngle);
      ret.y = this.cos(totalAngle);
      return ret;
    }
    /**
     * 三次方程式の三次項の係数が0になったときに補欠的に二次方程式の解をもとめる。
     * a * x^2 + b * x + c = 0
     *
     * @param   a -> 二次項の係数値
     * @param   b -> 一次項の係数値
     * @param   c -> 定数項の値
     * @return  二次方程式の解
     */
    static quadraticEquation(a, b, c) {
      if (this.abs(a) < _CubismMath.Epsilon) {
        if (this.abs(b) < _CubismMath.Epsilon) {
          return -c;
        }
        return -c / b;
      }
      return -(b + this.sqrt(b * b - 4 * a * c)) / (2 * a);
    }
    /**
     * カルダノの公式によってベジェのt値に該当する３次方程式の解を求める。
     * 重解になったときには0.0～1.0の値になる解を返す。
     *
     * a * x^3 + b * x^2 + c * x + d = 0
     *
     * @param   a -> 三次項の係数値
     * @param   b -> 二次項の係数値
     * @param   c -> 一次項の係数値
     * @param   d -> 定数項の値
     * @return  0.0～1.0の間にある解
     */
    static cardanoAlgorithmForBezier(a, b, c, d) {
      if (this.sqrt(a) < _CubismMath.Epsilon) {
        return this.range(this.quadraticEquation(b, c, d), 0, 1);
      }
      const ba = b / a;
      const ca = c / a;
      const da = d / a;
      const p = (3 * ca - ba * ba) / 3;
      const p3 = p / 3;
      const q = (2 * ba * ba * ba - 9 * ba * ca + 27 * da) / 27;
      const q2 = q / 2;
      const discriminant = q2 * q2 + p3 * p3 * p3;
      const center = 0.5;
      const threshold = center + 0.01;
      if (discriminant < 0) {
        const mp3 = -p / 3;
        const mp33 = mp3 * mp3 * mp3;
        const r = this.sqrt(mp33);
        const t = -q / (2 * r);
        const cosphi = this.range(t, -1, 1);
        const phi = Math.acos(cosphi);
        const crtr = this.cbrt(r);
        const t1 = 2 * crtr;
        const root12 = t1 * this.cos(phi / 3) - ba / 3;
        if (this.abs(root12 - center) < threshold) {
          return this.range(root12, 0, 1);
        }
        const root2 = t1 * this.cos((phi + 2 * Math.PI) / 3) - ba / 3;
        if (this.abs(root2 - center) < threshold) {
          return this.range(root2, 0, 1);
        }
        const root3 = t1 * this.cos((phi + 4 * Math.PI) / 3) - ba / 3;
        return this.range(root3, 0, 1);
      }
      if (discriminant == 0) {
        let u12;
        if (q2 < 0) {
          u12 = this.cbrt(-q2);
        } else {
          u12 = -this.cbrt(q2);
        }
        const root12 = 2 * u12 - ba / 3;
        if (this.abs(root12 - center) < threshold) {
          return this.range(root12, 0, 1);
        }
        const root2 = -u12 - ba / 3;
        return this.range(root2, 0, 1);
      }
      const sd = this.sqrt(discriminant);
      const u1 = this.cbrt(sd - q2);
      const v1 = this.cbrt(sd + q2);
      const root1 = u1 - v1 - ba / 3;
      return this.range(root1, 0, 1);
    }
    /**
     * 浮動小数点の余りを求める。
     *
     * @param dividend 被除数（割られる値）
     * @param divisor 除数（割る値）
     * @returns 余り
     */
    static mod(dividend, divisor) {
      if (!isFinite(dividend) || divisor === 0 || isNaN(dividend) || isNaN(divisor)) {
        console.warn(
          `divided: ${dividend}, divisor: ${divisor} mod() returns 'NaN'.`
        );
        return NaN;
      }
      const absDividend = Math.abs(dividend);
      const absDivisor = Math.abs(divisor);
      let result = absDividend - Math.floor(absDividend / absDivisor) * absDivisor;
      result *= Math.sign(dividend);
      return result;
    }
    /**
     * コンストラクタ
     */
    constructor() {
    }
  };
  __publicField(_CubismMath, "Epsilon", 1e-5);
  var CubismMath = _CubismMath;
  var Live2DCubismFramework20;
  ((Live2DCubismFramework42) => {
    Live2DCubismFramework42.CubismMath = CubismMath;
  })(Live2DCubismFramework20 || (Live2DCubismFramework20 = {}));

  // .trellis/workspace/lapp-runtime-src/src/renderer/WebSDK/Framework/src/math/cubismtargetpoint.ts
  var FrameRate = 30;
  var Epsilon2 = 0.01;
  var CubismTargetPoint = class {
    /**
     * コンストラクタ
     */
    constructor() {
      __publicField(this, "_faceTargetX");
      // 顔の向きのX目標値（この値に近づいていく）
      __publicField(this, "_faceTargetY");
      // 顔の向きのY目標値（この値に近づいていく）
      __publicField(this, "_faceX");
      // 顔の向きX（-1.0 ~ 1.0）
      __publicField(this, "_faceY");
      // 顔の向きY（-1.0 ~ 1.0）
      __publicField(this, "_faceVX");
      // 顔の向きの変化速度X
      __publicField(this, "_faceVY");
      // 顔の向きの変化速度Y
      __publicField(this, "_lastTimeSeconds");
      // 最後の実行時間[秒]
      __publicField(this, "_userTimeSeconds");
      this._faceTargetX = 0;
      this._faceTargetY = 0;
      this._faceX = 0;
      this._faceY = 0;
      this._faceVX = 0;
      this._faceVY = 0;
      this._lastTimeSeconds = 0;
      this._userTimeSeconds = 0;
    }
    /**
     * 更新処理
     */
    update(deltaTimeSeconds) {
      this._userTimeSeconds += deltaTimeSeconds;
      const faceParamMaxV = 40 / 10;
      const maxV = faceParamMaxV * 1 / FrameRate;
      if (this._lastTimeSeconds == 0) {
        this._lastTimeSeconds = this._userTimeSeconds;
        return;
      }
      const deltaTimeWeight = (this._userTimeSeconds - this._lastTimeSeconds) * FrameRate;
      this._lastTimeSeconds = this._userTimeSeconds;
      const timeToMaxSpeed = 0.15;
      const frameToMaxSpeed = timeToMaxSpeed * FrameRate;
      const maxA = deltaTimeWeight * maxV / frameToMaxSpeed;
      const dx = this._faceTargetX - this._faceX;
      const dy = this._faceTargetY - this._faceY;
      if (CubismMath.abs(dx) <= Epsilon2 && CubismMath.abs(dy) <= Epsilon2) {
        return;
      }
      const d = CubismMath.sqrt(dx * dx + dy * dy);
      const vx = maxV * dx / d;
      const vy = maxV * dy / d;
      let ax = vx - this._faceVX;
      let ay = vy - this._faceVY;
      const a = CubismMath.sqrt(ax * ax + ay * ay);
      if (a < -maxA || a > maxA) {
        ax *= maxA / a;
        ay *= maxA / a;
      }
      this._faceVX += ax;
      this._faceVY += ay;
      {
        const maxV2 = 0.5 * (CubismMath.sqrt(maxA * maxA + 16 * maxA * d - 8 * maxA * d) - maxA);
        const curV = CubismMath.sqrt(
          this._faceVX * this._faceVX + this._faceVY * this._faceVY
        );
        if (curV > maxV2) {
          this._faceVX *= maxV2 / curV;
          this._faceVY *= maxV2 / curV;
        }
      }
      this._faceX += this._faceVX;
      this._faceY += this._faceVY;
    }
    /**
     * X軸の顔の向きの値を取得
     *
     * @return X軸の顔の向きの値（-1.0 ~ 1.0）
     */
    getX() {
      return this._faceX;
    }
    /**
     * Y軸の顔の向きの値を取得
     *
     * @return Y軸の顔の向きの値（-1.0 ~ 1.0）
     */
    getY() {
      return this._faceY;
    }
    /**
     * 顔の向きの目標値を設定
     *
     * @param x X軸の顔の向きの値（-1.0 ~ 1.0）
     * @param y Y軸の顔の向きの値（-1.0 ~ 1.0）
     */
    set(x, y) {
      this._faceTargetX = x;
      this._faceTargetY = y;
    }
    // デルタ時間の積算値[秒]
  };
  var Live2DCubismFramework21;
  ((Live2DCubismFramework42) => {
    Live2DCubismFramework42.CubismTargetPoint = CubismTargetPoint;
  })(Live2DCubismFramework21 || (Live2DCubismFramework21 = {}));

  // .trellis/workspace/lapp-runtime-src/src/renderer/WebSDK/Framework/src/motion/acubismmotion.ts
  var ACubismMotion = class {
    /**
     * コンストラクタ
     */
    constructor() {
      /**
       * モーション再生終了コールバックの登録
       *
       * モーション再生終了コールバックを登録する。
       * isFinishedフラグを設定するタイミングで呼び出される。
       * 以下の状態の際には呼び出されない:
       *   1. 再生中のモーションが「ループ」として設定されているとき
       *   2. コールバックが登録されていない時
       *
       * @param onFinishedMotionHandler モーション再生終了コールバック関数
       */
      __publicField(this, "setFinishedMotionHandler", (onFinishedMotionHandler) => this._onFinishedMotion = onFinishedMotionHandler);
      /**
       * モーション再生終了コールバックの取得
       *
       * モーション再生終了コールバックを取得する。
       *
       * @return 登録されているモーション再生終了コールバック関数
       */
      __publicField(this, "getFinishedMotionHandler", () => this._onFinishedMotion);
      __publicField(this, "_fadeInSeconds");
      // フェードインにかかる時間[秒]
      __publicField(this, "_fadeOutSeconds");
      // フェードアウトにかかる時間[秒]
      __publicField(this, "_weight");
      // モーションの重み
      __publicField(this, "_offsetSeconds");
      // モーション再生の開始時間[秒]
      __publicField(this, "_firedEventValues");
      // モーション再生終了コールバック関数
      __publicField(this, "_onFinishedMotion");
      this._fadeInSeconds = -1;
      this._fadeOutSeconds = -1;
      this._weight = 1;
      this._offsetSeconds = 0;
      this._firedEventValues = new csmVector();
    }
    /**
     * インスタンスの破棄
     */
    static delete(motion) {
      motion.release();
      motion = null;
    }
    /**
     * デストラクタ相当の処理
     */
    release() {
      this._weight = 0;
    }
    /**
     * モデルのパラメータ
     * @param model 対象のモデル
     * @param motionQueueEntry CubismMotionQueueManagerで管理されているモーション
     * @param userTimeSeconds デルタ時間の積算値[秒]
     */
    updateParameters(model, motionQueueEntry, userTimeSeconds) {
      if (!motionQueueEntry.isAvailable() || motionQueueEntry.isFinished()) {
        return;
      }
      this.setupMotionQueueEntry(motionQueueEntry, userTimeSeconds);
      const fadeWeight = this.updateFadeWeight(motionQueueEntry, userTimeSeconds);
      this.doUpdateParameters(
        model,
        userTimeSeconds,
        fadeWeight,
        motionQueueEntry
      );
      if (motionQueueEntry.getEndTime() > 0 && motionQueueEntry.getEndTime() < userTimeSeconds) {
        motionQueueEntry.setIsFinished(true);
      }
    }
    /**
     * @brief モデルの再生開始処理
     *
     * モーションの再生を開始するためのセットアップを行う。
     *
     * @param[in]   motionQueueEntry    CubismMotionQueueManagerで管理されているモーション
     * @param[in]   userTimeSeconds     デルタ時間の積算値[秒]
     */
    setupMotionQueueEntry(motionQueueEntry, userTimeSeconds) {
      if (motionQueueEntry == null || motionQueueEntry.isStarted()) {
        return;
      }
      if (!motionQueueEntry.isAvailable()) {
        return;
      }
      motionQueueEntry.setIsStarted(true);
      motionQueueEntry.setStartTime(userTimeSeconds - this._offsetSeconds);
      motionQueueEntry.setFadeInStartTime(userTimeSeconds);
      const duration = this.getDuration();
      if (motionQueueEntry.getEndTime() < 0) {
        motionQueueEntry.setEndTime(
          duration <= 0 ? -1 : motionQueueEntry.getStartTime() + duration
        );
      }
    }
    /**
     * @brief モデルのウェイト更新
     *
     * モーションのウェイトを更新する。
     *
     * @param[in]   motionQueueEntry    CubismMotionQueueManagerで管理されているモーション
     * @param[in]   userTimeSeconds     デルタ時間の積算値[秒]
     */
    updateFadeWeight(motionQueueEntry, userTimeSeconds) {
      if (motionQueueEntry == null) {
        CubismDebug.print(4 /* LogLevel_Error */, "motionQueueEntry is null.");
      }
      let fadeWeight = this._weight;
      const fadeIn = this._fadeInSeconds == 0 ? 1 : CubismMath.getEasingSine(
        (userTimeSeconds - motionQueueEntry.getFadeInStartTime()) / this._fadeInSeconds
      );
      const fadeOut = this._fadeOutSeconds == 0 || motionQueueEntry.getEndTime() < 0 ? 1 : CubismMath.getEasingSine(
        (motionQueueEntry.getEndTime() - userTimeSeconds) / this._fadeOutSeconds
      );
      fadeWeight = fadeWeight * fadeIn * fadeOut;
      motionQueueEntry.setState(userTimeSeconds, fadeWeight);
      CSM_ASSERT(0 <= fadeWeight && fadeWeight <= 1);
      return fadeWeight;
    }
    /**
     * フェードインの時間を設定する
     * @param fadeInSeconds フェードインにかかる時間[秒]
     */
    setFadeInTime(fadeInSeconds) {
      this._fadeInSeconds = fadeInSeconds;
    }
    /**
     * フェードアウトの時間を設定する
     * @param fadeOutSeconds フェードアウトにかかる時間[秒]
     */
    setFadeOutTime(fadeOutSeconds) {
      this._fadeOutSeconds = fadeOutSeconds;
    }
    /**
     * フェードアウトにかかる時間の取得
     * @return フェードアウトにかかる時間[秒]
     */
    getFadeOutTime() {
      return this._fadeOutSeconds;
    }
    /**
     * フェードインにかかる時間の取得
     * @return フェードインにかかる時間[秒]
     */
    getFadeInTime() {
      return this._fadeInSeconds;
    }
    /**
     * モーション適用の重みの設定
     * @param weight 重み（0.0 - 1.0）
     */
    setWeight(weight) {
      this._weight = weight;
    }
    /**
     * モーション適用の重みの取得
     * @return 重み（0.0 - 1.0）
     */
    getWeight() {
      return this._weight;
    }
    /**
     * モーションの長さの取得
     * @return モーションの長さ[秒]
     *
     * @note ループの時は「-1」。
     *       ループでない場合は、オーバーライドする。
     *       正の値の時は取得される時間で終了する。
     *       「-1」の時は外部から停止命令がない限り終わらない処理となる。
     */
    getDuration() {
      return -1;
    }
    /**
     * モーションのループ1回分の長さの取得
     * @return モーションのループ一回分の長さ[秒]
     *
     * @note ループしない場合は、getDuration()と同じ値を返す
     *       ループ一回分の長さが定義できない場合(プログラム的に動き続けるサブクラスなど)の場合は「-1」を返す
     */
    getLoopDuration() {
      return -1;
    }
    /**
     * モーション再生の開始時刻の設定
     * @param offsetSeconds モーション再生の開始時刻[秒]
     */
    setOffsetTime(offsetSeconds) {
      this._offsetSeconds = offsetSeconds;
    }
    /**
     * モデルのパラメータ更新
     *
     * イベント発火のチェック。
     * 入力する時間は呼ばれるモーションタイミングを０とした秒数で行う。
     *
     * @param beforeCheckTimeSeconds 前回のイベントチェック時間[秒]
     * @param motionTimeSeconds 今回の再生時間[秒]
     */
    getFiredEvent(beforeCheckTimeSeconds, motionTimeSeconds) {
      return this._firedEventValues;
    }
    /**
     * 透明度のカーブが存在するかどうかを確認する
     *
     * @returns true  -> キーが存在する
     *          false -> キーが存在しない
     */
    isExistModelOpacity() {
      return false;
    }
    /**
     * 透明度のカーブのインデックスを返す
     *
     * @returns success:透明度のカーブのインデックス
     */
    getModelOpacityIndex() {
      return -1;
    }
    /**
     * 透明度のIdを返す
     *
     * @param index モーションカーブのインデックス
     * @returns success:透明度のId
     */
    getModelOpacityId(index) {
      return null;
    }
    /**
     * 指定時間の透明度の値を返す
     *
     * @returns success:モーションの現在時間におけるOpacityの値
     *
     * @note  更新後の値を取るにはUpdateParameters() の後に呼び出す。
     */
    getModelOpacityValue() {
      return 1;
    }
  };
  var Live2DCubismFramework22;
  ((Live2DCubismFramework42) => {
    Live2DCubismFramework42.ACubismMotion = ACubismMotion;
  })(Live2DCubismFramework22 || (Live2DCubismFramework22 = {}));

  // .trellis/workspace/lapp-runtime-src/src/renderer/WebSDK/Framework/src/motion/cubismexpressionmotion.ts
  var ExpressionKeyFadeIn = "FadeInTime";
  var ExpressionKeyFadeOut = "FadeOutTime";
  var ExpressionKeyParameters = "Parameters";
  var ExpressionKeyId = "Id";
  var ExpressionKeyValue = "Value";
  var ExpressionKeyBlend = "Blend";
  var BlendValueAdd = "Add";
  var BlendValueMultiply = "Multiply";
  var BlendValueOverwrite = "Overwrite";
  var DefaultFadeTime = 1;
  var _CubismExpressionMotion = class _CubismExpressionMotion extends ACubismMotion {
    /**
     * コンストラクタ
     */
    constructor() {
      super();
      __publicField(this, "_parameters");
      // 表情のパラメータ情報リスト
      /**
       * 表情の現在のウェイト
       *
       * @deprecated 不具合を引き起こす要因となるため非推奨。
       */
      __publicField(this, "_fadeWeight");
      this._parameters = new csmVector();
      this._fadeWeight = 0;
    }
    // 乗算適用の初期値
    /**
     * インスタンスを作成する。
     * @param buffer expファイルが読み込まれているバッファ
     * @param size バッファのサイズ
     * @return 作成されたインスタンス
     */
    static create(buffer, size) {
      const expression = new _CubismExpressionMotion();
      expression.parse(buffer, size);
      return expression;
    }
    /**
     * モデルのパラメータの更新の実行
     * @param model 対象のモデル
     * @param userTimeSeconds デルタ時間の積算値[秒]
     * @param weight モーションの重み
     * @param motionQueueEntry CubismMotionQueueManagerで管理されているモーション
     */
    doUpdateParameters(model, userTimeSeconds, weight, motionQueueEntry) {
      for (let i = 0; i < this._parameters.getSize(); ++i) {
        const parameter = this._parameters.at(i);
        switch (parameter.blendType) {
          case 0 /* Additive */: {
            model.addParameterValueById(
              parameter.parameterId,
              parameter.value,
              weight
            );
            break;
          }
          case 1 /* Multiply */: {
            model.multiplyParameterValueById(
              parameter.parameterId,
              parameter.value,
              weight
            );
            break;
          }
          case 2 /* Overwrite */: {
            model.setParameterValueById(
              parameter.parameterId,
              parameter.value,
              weight
            );
            break;
          }
          default:
            break;
        }
      }
    }
    /**
     * @brief 表情によるモデルのパラメータの計算
     *
     * モデルの表情に関するパラメータを計算する。
     *
     * @param[in]   model                        対象のモデル
     * @param[in]   userTimeSeconds              デルタ時間の積算値[秒]
     * @param[in]   motionQueueEntry             CubismMotionQueueManagerで管理されているモーション
     * @param[in]   expressionParameterValues    モデルに適用する各パラメータの値
     * @param[in]   expressionIndex              表情のインデックス
     * @param[in]   fadeWeight                   表情のウェイト
     */
    calculateExpressionParameters(model, userTimeSeconds, motionQueueEntry, expressionParameterValues, expressionIndex, fadeWeight) {
      if (motionQueueEntry == null || expressionParameterValues == null) {
        return;
      }
      if (!motionQueueEntry.isAvailable()) {
        return;
      }
      this._fadeWeight = this.updateFadeWeight(motionQueueEntry, userTimeSeconds);
      for (let i = 0; i < expressionParameterValues.getSize(); ++i) {
        const expressionParameterValue = expressionParameterValues.at(i);
        if (expressionParameterValue.parameterId == null) {
          continue;
        }
        const currentParameterValue = expressionParameterValue.overwriteValue = model.getParameterValueById(expressionParameterValue.parameterId);
        const expressionParameters = this.getExpressionParameters();
        let parameterIndex = -1;
        for (let j = 0; j < expressionParameters.getSize(); ++j) {
          if (expressionParameterValue.parameterId != expressionParameters.at(j).parameterId) {
            continue;
          }
          parameterIndex = j;
          break;
        }
        if (parameterIndex < 0) {
          if (expressionIndex == 0) {
            expressionParameterValue.additiveValue = _CubismExpressionMotion.DefaultAdditiveValue;
            expressionParameterValue.multiplyValue = _CubismExpressionMotion.DefaultMultiplyValue;
            expressionParameterValue.overwriteValue = currentParameterValue;
          } else {
            expressionParameterValue.additiveValue = this.calculateValue(
              expressionParameterValue.additiveValue,
              _CubismExpressionMotion.DefaultAdditiveValue,
              fadeWeight
            );
            expressionParameterValue.multiplyValue = this.calculateValue(
              expressionParameterValue.multiplyValue,
              _CubismExpressionMotion.DefaultMultiplyValue,
              fadeWeight
            );
            expressionParameterValue.overwriteValue = this.calculateValue(
              expressionParameterValue.overwriteValue,
              currentParameterValue,
              fadeWeight
            );
          }
          continue;
        }
        const value = expressionParameters.at(parameterIndex).value;
        let newAdditiveValue, newMultiplyValue, newOverwriteValue;
        switch (expressionParameters.at(parameterIndex).blendType) {
          case 0 /* Additive */:
            newAdditiveValue = value;
            newMultiplyValue = _CubismExpressionMotion.DefaultMultiplyValue;
            newOverwriteValue = currentParameterValue;
            break;
          case 1 /* Multiply */:
            newAdditiveValue = _CubismExpressionMotion.DefaultAdditiveValue;
            newMultiplyValue = value;
            newOverwriteValue = currentParameterValue;
            break;
          case 2 /* Overwrite */:
            newAdditiveValue = _CubismExpressionMotion.DefaultAdditiveValue;
            newMultiplyValue = _CubismExpressionMotion.DefaultMultiplyValue;
            newOverwriteValue = value;
            break;
          default:
            return;
        }
        if (expressionIndex == 0) {
          expressionParameterValue.additiveValue = newAdditiveValue;
          expressionParameterValue.multiplyValue = newMultiplyValue;
          expressionParameterValue.overwriteValue = newOverwriteValue;
        } else {
          expressionParameterValue.additiveValue = expressionParameterValue.additiveValue * (1 - fadeWeight) + newAdditiveValue * fadeWeight;
          expressionParameterValue.multiplyValue = expressionParameterValue.multiplyValue * (1 - fadeWeight) + newMultiplyValue * fadeWeight;
          expressionParameterValue.overwriteValue = expressionParameterValue.overwriteValue * (1 - fadeWeight) + newOverwriteValue * fadeWeight;
        }
      }
    }
    /**
     * @brief 表情が参照しているパラメータを取得
     *
     * 表情が参照しているパラメータを取得する
     *
     * @return 表情パラメータ
     */
    getExpressionParameters() {
      return this._parameters;
    }
    /**
     * @brief 表情のフェードの値を取得
     *
     * 現在の表情のフェードのウェイト値を取得する
     *
     * @returns 表情のフェードのウェイト値
     *
     * @deprecated CubismExpressionMotion.fadeWeightが削除予定のため非推奨。
     * CubismExpressionMotionManager.getFadeWeight(index: number): number を使用してください。
     * @see CubismExpressionMotionManager#getFadeWeight(index: number)
     */
    getFadeWeight() {
      return this._fadeWeight;
    }
    parse(buffer, size) {
      const json = CubismJson.create(buffer, size);
      if (!json) {
        return;
      }
      const root = json.getRoot();
      this.setFadeInTime(
        root.getValueByString(ExpressionKeyFadeIn).toFloat(DefaultFadeTime)
      );
      this.setFadeOutTime(
        root.getValueByString(ExpressionKeyFadeOut).toFloat(DefaultFadeTime)
      );
      const parameterCount = root.getValueByString(ExpressionKeyParameters).getSize();
      this._parameters.prepareCapacity(parameterCount);
      for (let i = 0; i < parameterCount; ++i) {
        const param = root.getValueByString(ExpressionKeyParameters).getValueByIndex(i);
        const parameterId = CubismFramework.getIdManager().getId(
          param.getValueByString(ExpressionKeyId).getRawString()
        );
        const value = param.getValueByString(ExpressionKeyValue).toFloat();
        let blendType;
        if (param.getValueByString(ExpressionKeyBlend).isNull() || param.getValueByString(ExpressionKeyBlend).getString() == BlendValueAdd) {
          blendType = 0 /* Additive */;
        } else if (param.getValueByString(ExpressionKeyBlend).getString() == BlendValueMultiply) {
          blendType = 1 /* Multiply */;
        } else if (param.getValueByString(ExpressionKeyBlend).getString() == BlendValueOverwrite) {
          blendType = 2 /* Overwrite */;
        } else {
          blendType = 0 /* Additive */;
        }
        const item = new ExpressionParameter();
        item.parameterId = parameterId;
        item.blendType = blendType;
        item.value = value;
        this._parameters.pushBack(item);
      }
      CubismJson.delete(json);
    }
    /**
     * @brief ブレンド計算
     *
     * 入力された値でブレンド計算をする。
     *
     * @param source 現在の値
     * @param destination 適用する値
     * @param weight ウェイト
     * @returns 計算結果
     */
    calculateValue(source, destination, fadeWeight) {
      return source * (1 - fadeWeight) + destination * fadeWeight;
    }
  };
  __publicField(_CubismExpressionMotion, "DefaultAdditiveValue", 0);
  // 加算適用の初期値
  __publicField(_CubismExpressionMotion, "DefaultMultiplyValue", 1);
  var CubismExpressionMotion = _CubismExpressionMotion;
  var ExpressionBlendType = /* @__PURE__ */ ((ExpressionBlendType2) => {
    ExpressionBlendType2[ExpressionBlendType2["Additive"] = 0] = "Additive";
    ExpressionBlendType2[ExpressionBlendType2["Multiply"] = 1] = "Multiply";
    ExpressionBlendType2[ExpressionBlendType2["Overwrite"] = 2] = "Overwrite";
    return ExpressionBlendType2;
  })(ExpressionBlendType || {});
  var ExpressionParameter = class {
    constructor() {
      __publicField(this, "parameterId");
      // パラメータID
      __publicField(this, "blendType");
      // パラメータの演算種類
      __publicField(this, "value");
    }
    // 値
  };
  var Live2DCubismFramework23;
  ((Live2DCubismFramework42) => {
    Live2DCubismFramework42.CubismExpressionMotion = CubismExpressionMotion;
    Live2DCubismFramework42.ExpressionBlendType = ExpressionBlendType;
    Live2DCubismFramework42.ExpressionParameter = ExpressionParameter;
  })(Live2DCubismFramework23 || (Live2DCubismFramework23 = {}));

  // .trellis/workspace/lapp-runtime-src/src/renderer/WebSDK/Framework/src/motion/cubismmotionqueueentry.ts
  var CubismMotionQueueEntry = class {
    /**
     * コンストラクタ
     */
    constructor() {
      __publicField(this, "_autoDelete");
      // 自動削除
      __publicField(this, "_motion");
      // モーション
      __publicField(this, "_available");
      // 有効化フラグ
      __publicField(this, "_finished");
      // 終了フラグ
      __publicField(this, "_started");
      // 開始フラグ
      __publicField(this, "_startTimeSeconds");
      // モーション再生開始時刻[秒]
      __publicField(this, "_fadeInStartTimeSeconds");
      // フェードイン開始時刻（ループの時は初回のみ）[秒]
      __publicField(this, "_endTimeSeconds");
      // 終了予定時刻[秒]
      __publicField(this, "_stateTimeSeconds");
      // 時刻の状態[秒]
      __publicField(this, "_stateWeight");
      // 重みの状態
      __publicField(this, "_lastEventCheckSeconds");
      // 最終のMotion側のチェックした時間
      __publicField(this, "_fadeOutSeconds");
      // フェードアウト時間[秒]
      __publicField(this, "_isTriggeredFadeOut");
      // フェードアウト開始フラグ
      __publicField(this, "_motionQueueEntryHandle");
      this._autoDelete = false;
      this._motion = null;
      this._available = true;
      this._finished = false;
      this._started = false;
      this._startTimeSeconds = -1;
      this._fadeInStartTimeSeconds = 0;
      this._endTimeSeconds = -1;
      this._stateTimeSeconds = 0;
      this._stateWeight = 0;
      this._lastEventCheckSeconds = 0;
      this._motionQueueEntryHandle = this;
      this._fadeOutSeconds = 0;
      this._isTriggeredFadeOut = false;
    }
    /**
     * デストラクタ相当の処理
     */
    release() {
      if (this._autoDelete && this._motion) {
        ACubismMotion.delete(this._motion);
      }
    }
    /**
     * フェードアウト時間と開始判定の設定
     * @param fadeOutSeconds フェードアウトにかかる時間[秒]
     */
    setFadeOut(fadeOutSeconds) {
      this._fadeOutSeconds = fadeOutSeconds;
      this._isTriggeredFadeOut = true;
    }
    /**
     * フェードアウトの開始
     * @param fadeOutSeconds フェードアウトにかかる時間[秒]
     * @param userTimeSeconds デルタ時間の積算値[秒]
     */
    startFadeOut(fadeOutSeconds, userTimeSeconds) {
      const newEndTimeSeconds = userTimeSeconds + fadeOutSeconds;
      this._isTriggeredFadeOut = true;
      if (this._endTimeSeconds < 0 || newEndTimeSeconds < this._endTimeSeconds) {
        this._endTimeSeconds = newEndTimeSeconds;
      }
    }
    /**
     * モーションの終了の確認
     *
     * @return true モーションが終了した
     * @return false 終了していない
     */
    isFinished() {
      return this._finished;
    }
    /**
     * モーションの開始の確認
     * @return true モーションが開始した
     * @return false 開始していない
     */
    isStarted() {
      return this._started;
    }
    /**
     * モーションの開始時刻の取得
     * @return モーションの開始時刻[秒]
     */
    getStartTime() {
      return this._startTimeSeconds;
    }
    /**
     * フェードインの開始時刻の取得
     * @return フェードインの開始時刻[秒]
     */
    getFadeInStartTime() {
      return this._fadeInStartTimeSeconds;
    }
    /**
     * フェードインの終了時刻の取得
     * @return フェードインの終了時刻の取得
     */
    getEndTime() {
      return this._endTimeSeconds;
    }
    /**
     * モーションの開始時刻の設定
     * @param startTime モーションの開始時刻
     */
    setStartTime(startTime) {
      this._startTimeSeconds = startTime;
    }
    /**
     * フェードインの開始時刻の設定
     * @param startTime フェードインの開始時刻[秒]
     */
    setFadeInStartTime(startTime) {
      this._fadeInStartTimeSeconds = startTime;
    }
    /**
     * フェードインの終了時刻の設定
     * @param endTime フェードインの終了時刻[秒]
     */
    setEndTime(endTime) {
      this._endTimeSeconds = endTime;
    }
    /**
     * モーションの終了の設定
     * @param f trueならモーションの終了
     */
    setIsFinished(f) {
      this._finished = f;
    }
    /**
     * モーション開始の設定
     * @param f trueならモーションの開始
     */
    setIsStarted(f) {
      this._started = f;
    }
    /**
     * モーションの有効性の確認
     * @return true モーションは有効
     * @return false モーションは無効
     */
    isAvailable() {
      return this._available;
    }
    /**
     * モーションの有効性の設定
     * @param v trueならモーションは有効
     */
    setIsAvailable(v) {
      this._available = v;
    }
    /**
     * モーションの状態の設定
     * @param timeSeconds 現在時刻[秒]
     * @param weight モーション尾重み
     */
    setState(timeSeconds, weight) {
      this._stateTimeSeconds = timeSeconds;
      this._stateWeight = weight;
    }
    /**
     * モーションの現在時刻の取得
     * @return モーションの現在時刻[秒]
     */
    getStateTime() {
      return this._stateTimeSeconds;
    }
    /**
     * モーションの重みの取得
     * @return モーションの重み
     */
    getStateWeight() {
      return this._stateWeight;
    }
    /**
     * 最後にイベントの発火をチェックした時間を取得
     *
     * @return 最後にイベントの発火をチェックした時間[秒]
     */
    getLastCheckEventSeconds() {
      return this._lastEventCheckSeconds;
    }
    /**
     * 最後にイベントをチェックした時間を設定
     * @param checkSeconds 最後にイベントをチェックした時間[秒]
     */
    setLastCheckEventSeconds(checkSeconds) {
      this._lastEventCheckSeconds = checkSeconds;
    }
    /**
     * フェードアウト開始判定の取得
     * @return フェードアウト開始するかどうか
     */
    isTriggeredFadeOut() {
      return this._isTriggeredFadeOut;
    }
    /**
     * フェードアウト時間の取得
     * @return フェードアウト時間[秒]
     */
    getFadeOutSeconds() {
      return this._fadeOutSeconds;
    }
    /**
     * モーションの取得
     *
     * @return モーション
     */
    getCubismMotion() {
      return this._motion;
    }
    // インスタンスごとに一意の値を持つ識別番号
  };
  var Live2DCubismFramework24;
  ((Live2DCubismFramework42) => {
    Live2DCubismFramework42.CubismMotionQueueEntry = CubismMotionQueueEntry;
  })(Live2DCubismFramework24 || (Live2DCubismFramework24 = {}));

  // .trellis/workspace/lapp-runtime-src/src/renderer/WebSDK/Framework/src/motion/cubismmotionqueuemanager.ts
  var CubismMotionQueueManager = class {
    /**
     * コンストラクタ
     */
    constructor() {
      __publicField(this, "_userTimeSeconds");
      // デルタ時間の積算値[秒]
      __publicField(this, "_motions");
      // モーション
      __publicField(this, "_eventCallBack");
      // コールバック関数
      __publicField(this, "_eventCustomData");
      this._userTimeSeconds = 0;
      this._eventCallBack = null;
      this._eventCustomData = null;
      this._motions = new csmVector();
    }
    /**
     * デストラクタ
     */
    release() {
      for (let i = 0; i < this._motions.getSize(); ++i) {
        if (this._motions.at(i)) {
          this._motions.at(i).release();
          this._motions.set(i, null);
        }
      }
      this._motions = null;
    }
    /**
     * 指定したモーションの開始
     *
     * 指定したモーションを開始する。同じタイプのモーションが既にある場合は、既存のモーションに終了フラグを立て、フェードアウトを開始させる。
     *
     * @param   motion          開始するモーション
     * @param   autoDelete      再生が終了したモーションのインスタンスを削除するなら true
     * @param   userTimeSeconds Deprecated: デルタ時間の積算値[秒] 関数内で参照していないため使用は非推奨。
     * @return                      開始したモーションの識別番号を返す。個別のモーションが終了したか否かを判定するIsFinished()の引数で使用する。開始できない時は「-1」
     */
    startMotion(motion, autoDelete, userTimeSeconds) {
      if (motion == null) {
        return InvalidMotionQueueEntryHandleValue;
      }
      let motionQueueEntry = null;
      for (let i = 0; i < this._motions.getSize(); ++i) {
        motionQueueEntry = this._motions.at(i);
        if (motionQueueEntry == null) {
          continue;
        }
        motionQueueEntry.setFadeOut(motionQueueEntry._motion.getFadeOutTime());
      }
      motionQueueEntry = new CubismMotionQueueEntry();
      motionQueueEntry._autoDelete = autoDelete;
      motionQueueEntry._motion = motion;
      this._motions.pushBack(motionQueueEntry);
      return motionQueueEntry._motionQueueEntryHandle;
    }
    /**
     * 全てのモーションの終了の確認
     * @return true 全て終了している
     * @return false 終了していない
     */
    isFinished() {
      for (let ite = this._motions.begin(); ite.notEqual(this._motions.end()); ) {
        let motionQueueEntry = ite.ptr();
        if (motionQueueEntry == null) {
          ite = this._motions.erase(ite);
          continue;
        }
        const motion = motionQueueEntry._motion;
        if (motion == null) {
          motionQueueEntry.release();
          motionQueueEntry = null;
          ite = this._motions.erase(ite);
          continue;
        }
        if (!motionQueueEntry.isFinished()) {
          return false;
        } else {
          ite.preIncrement();
        }
      }
      return true;
    }
    /**
     * 指定したモーションの終了の確認
     * @param motionQueueEntryNumber モーションの識別番号
     * @return true 全て終了している
     * @return false 終了していない
     */
    isFinishedByHandle(motionQueueEntryNumber) {
      for (let ite = this._motions.begin(); ite.notEqual(this._motions.end()); ite.increment()) {
        const motionQueueEntry = ite.ptr();
        if (motionQueueEntry == null) {
          continue;
        }
        if (motionQueueEntry._motionQueueEntryHandle == motionQueueEntryNumber && !motionQueueEntry.isFinished()) {
          return false;
        }
      }
      return true;
    }
    /**
     * 全てのモーションを停止する
     */
    stopAllMotions() {
      for (let ite = this._motions.begin(); ite.notEqual(this._motions.end()); ) {
        let motionQueueEntry = ite.ptr();
        if (motionQueueEntry == null) {
          ite = this._motions.erase(ite);
          continue;
        }
        motionQueueEntry.release();
        motionQueueEntry = null;
        ite = this._motions.erase(ite);
      }
    }
    /**
     * @brief CubismMotionQueueEntryの配列の取得
     *
     * CubismMotionQueueEntryの配列を取得する。
     *
     * @return  CubismMotionQueueEntryの配列へのポインタ
     * @retval  NULL   見つからなかった
     */
    getCubismMotionQueueEntries() {
      return this._motions;
    }
    /**
       * 指定したCubismMotionQueueEntryの取得
    
       * @param   motionQueueEntryNumber  モーションの識別番号
       * @return  指定したCubismMotionQueueEntry
       * @return  null   見つからなかった
       */
    getCubismMotionQueueEntry(motionQueueEntryNumber) {
      for (let ite = this._motions.begin(); ite.notEqual(this._motions.end()); ite.preIncrement()) {
        const motionQueueEntry = ite.ptr();
        if (motionQueueEntry == null) {
          continue;
        }
        if (motionQueueEntry._motionQueueEntryHandle == motionQueueEntryNumber) {
          return motionQueueEntry;
        }
      }
      return null;
    }
    /**
     * イベントを受け取るCallbackの登録
     *
     * @param callback コールバック関数
     * @param customData コールバックに返されるデータ
     */
    setEventCallback(callback, customData = null) {
      this._eventCallBack = callback;
      this._eventCustomData = customData;
    }
    /**
     * モーションを更新して、モデルにパラメータ値を反映する。
     *
     * @param   model   対象のモデル
     * @param   userTimeSeconds   デルタ時間の積算値[秒]
     * @return  true    モデルへパラメータ値の反映あり
     * @return  false   モデルへパラメータ値の反映なし(モーションの変化なし)
     */
    doUpdateMotion(model, userTimeSeconds) {
      let updated = false;
      for (let ite = this._motions.begin(); ite.notEqual(this._motions.end()); ) {
        let motionQueueEntry = ite.ptr();
        if (motionQueueEntry == null) {
          ite = this._motions.erase(ite);
          continue;
        }
        const motion = motionQueueEntry._motion;
        if (motion == null) {
          motionQueueEntry.release();
          motionQueueEntry = null;
          ite = this._motions.erase(ite);
          continue;
        }
        motion.updateParameters(model, motionQueueEntry, userTimeSeconds);
        updated = true;
        const firedList = motion.getFiredEvent(
          motionQueueEntry.getLastCheckEventSeconds() - motionQueueEntry.getStartTime(),
          userTimeSeconds - motionQueueEntry.getStartTime()
        );
        for (let i = 0; i < firedList.getSize(); ++i) {
          this._eventCallBack(this, firedList.at(i), this._eventCustomData);
        }
        motionQueueEntry.setLastCheckEventSeconds(userTimeSeconds);
        if (motionQueueEntry.isFinished()) {
          motionQueueEntry.release();
          motionQueueEntry = null;
          ite = this._motions.erase(ite);
        } else {
          if (motionQueueEntry.isTriggeredFadeOut()) {
            motionQueueEntry.startFadeOut(
              motionQueueEntry.getFadeOutSeconds(),
              userTimeSeconds
            );
          }
          ite.preIncrement();
        }
      }
      return updated;
    }
    // コールバックに戻されるデータ
  };
  var InvalidMotionQueueEntryHandleValue = -1;
  var Live2DCubismFramework25;
  ((Live2DCubismFramework42) => {
    Live2DCubismFramework42.CubismMotionQueueManager = CubismMotionQueueManager;
    Live2DCubismFramework42.InvalidMotionQueueEntryHandleValue = InvalidMotionQueueEntryHandleValue;
  })(Live2DCubismFramework25 || (Live2DCubismFramework25 = {}));

  // .trellis/workspace/lapp-runtime-src/src/renderer/WebSDK/Framework/src/motion/cubismexpressionmotionmanager.ts
  var ExpressionParameterValue = class {
    constructor() {
      __publicField(this, "parameterId");
      // パラメーターID
      __publicField(this, "additiveValue");
      // 加算値
      __publicField(this, "multiplyValue");
      // 乗算値
      __publicField(this, "overwriteValue");
    }
    // 上書き値
  };
  var CubismExpressionMotionManager = class extends CubismMotionQueueManager {
    /**
     * コンストラクタ
     */
    constructor() {
      super();
      __publicField(this, "_expressionParameterValues");
      ///< モデルに適用する各パラメータの値
      __publicField(this, "_fadeWeights");
      ///< 再生中の表情のウェイト
      __publicField(this, "_currentPriority");
      ///< 現在再生中のモーションの優先度
      __publicField(this, "_reservePriority");
      ///< 再生予定のモーションの優先度。再生中は0になる。モーションファイルを別スレッドで読み込むときの機能。
      __publicField(this, "_startExpressionTime");
      this._currentPriority = 0;
      this._reservePriority = 0;
      this._expressionParameterValues = new csmVector();
      this._fadeWeights = new csmVector();
    }
    /**
     * デストラクタ相当の処理
     */
    release() {
      if (this._expressionParameterValues) {
        csmDelete(this._expressionParameterValues);
        this._expressionParameterValues = null;
      }
      if (this._fadeWeights) {
        csmDelete(this._fadeWeights);
        this._fadeWeights = null;
      }
    }
    /**
     * @brief 再生中のモーションの優先度の取得
     *
     * 再生中のモーションの優先度を取得する。
     *
     * @returns モーションの優先度
     */
    getCurrentPriority() {
      return this._currentPriority;
    }
    /**
     * @brief 予約中のモーションの優先度の取得
     *
     * 予約中のモーションの優先度を取得する。
     *
     * @return  モーションの優先度
     */
    getReservePriority() {
      return this._reservePriority;
    }
    /**
     * @brief 再生中のモーションのウェイトを取得する。
     *
     * @param[in]    index    表情のインデックス
     * @returns               表情モーションのウェイト
     */
    getFadeWeight(index) {
      return this._fadeWeights.at(index);
    }
    /**
     * @brief 予約中のモーションの優先度の設定
     *
     * 予約中のモーションの優先度を設定する。
     *
     * @param[in]   priority     優先度
     */
    setReservePriority(priority) {
      this._reservePriority = priority;
    }
    /**
     * @brief 優先度を設定してモーションの開始
     *
     * 優先度を設定してモーションを開始する。
     *
     * @param[in]   motion          モーション
     * @param[in]   autoDelete      再生が終了したモーションのインスタンスを削除するならtrue
     * @param[in]   priority        優先度
     * @return                      開始したモーションの識別番号を返す。個別のモーションが終了したか否かを判定するIsFinished()の引数で使用する。開始できない時は「-1」
     */
    startMotionPriority(motion, autoDelete, priority) {
      if (priority == this.getReservePriority()) {
        this.setReservePriority(0);
      }
      this._currentPriority = priority;
      this._fadeWeights.pushBack(0);
      return this.startMotion(motion, autoDelete);
    }
    /**
     * @brief モーションの更新
     *
     * モーションを更新して、モデルにパラメータ値を反映する。
     *
     * @param[in]   model   対象のモデル
     * @param[in]   deltaTimeSeconds    デルタ時間[秒]
     * @retval  true    更新されている
     * @retval  false   更新されていない
     */
    updateMotion(model, deltaTimeSeconds) {
      this._userTimeSeconds += deltaTimeSeconds;
      let updated = false;
      const motions = this.getCubismMotionQueueEntries();
      let expressionWeight = 0;
      let expressionIndex = 0;
      for (let ite = this._motions.begin(); ite.notEqual(this._motions.end()); ) {
        const motionQueueEntry = ite.ptr();
        if (motionQueueEntry == null) {
          ite = motions.erase(ite);
          continue;
        }
        const expressionMotion = motionQueueEntry.getCubismMotion();
        if (expressionMotion == null) {
          csmDelete(motionQueueEntry);
          ite = motions.erase(ite);
          continue;
        }
        const expressionParameters = expressionMotion.getExpressionParameters();
        if (motionQueueEntry.isAvailable()) {
          for (let i = 0; i < expressionParameters.getSize(); ++i) {
            if (expressionParameters.at(i).parameterId == null) {
              continue;
            }
            let index = -1;
            for (let j = 0; j < this._expressionParameterValues.getSize(); ++j) {
              if (this._expressionParameterValues.at(j).parameterId != expressionParameters.at(i).parameterId) {
                continue;
              }
              index = j;
              break;
            }
            if (index >= 0) {
              continue;
            }
            const item = new ExpressionParameterValue();
            item.parameterId = expressionParameters.at(i).parameterId;
            item.additiveValue = CubismExpressionMotion.DefaultAdditiveValue;
            item.multiplyValue = CubismExpressionMotion.DefaultMultiplyValue;
            item.overwriteValue = model.getParameterValueById(item.parameterId);
            this._expressionParameterValues.pushBack(item);
          }
        }
        expressionMotion.setupMotionQueueEntry(
          motionQueueEntry,
          this._userTimeSeconds
        );
        this._fadeWeights.set(
          expressionIndex,
          expressionMotion.updateFadeWeight(
            motionQueueEntry,
            this._userTimeSeconds
          )
        );
        expressionMotion.calculateExpressionParameters(
          model,
          this._userTimeSeconds,
          motionQueueEntry,
          this._expressionParameterValues,
          expressionIndex,
          this._fadeWeights.at(expressionIndex)
        );
        expressionWeight += expressionMotion.getFadeInTime() == 0 ? 1 : CubismMath.getEasingSine(
          (this._userTimeSeconds - motionQueueEntry.getFadeInStartTime()) / expressionMotion.getFadeInTime()
        );
        updated = true;
        if (motionQueueEntry.isTriggeredFadeOut()) {
          motionQueueEntry.startFadeOut(
            motionQueueEntry.getFadeOutSeconds(),
            this._userTimeSeconds
          );
        }
        ite.preIncrement();
        ++expressionIndex;
      }
      if (motions.getSize() > 1) {
        const expressionMotion = motions.at(motions.getSize() - 1).getCubismMotion();
        const latestFadeWeight = this._fadeWeights.at(
          this._fadeWeights.getSize() - 1
        );
        if (latestFadeWeight >= 1) {
          for (let i = motions.getSize() - 2; i >= 0; --i) {
            const motionQueueEntry = motions.at(i);
            csmDelete(motionQueueEntry);
            motions.remove(i);
            this._fadeWeights.remove(i);
          }
        }
      }
      if (expressionWeight > 1) {
        expressionWeight = 1;
      }
      for (let i = 0; i < this._expressionParameterValues.getSize(); ++i) {
        const expressionParameterValue = this._expressionParameterValues.at(i);
        model.setParameterValueById(
          expressionParameterValue.parameterId,
          (expressionParameterValue.overwriteValue + expressionParameterValue.additiveValue) * expressionParameterValue.multiplyValue,
          expressionWeight
        );
        expressionParameterValue.additiveValue = CubismExpressionMotion.DefaultAdditiveValue;
        expressionParameterValue.multiplyValue = CubismExpressionMotion.DefaultMultiplyValue;
      }
      return updated;
    }
    ///< 表情の再生開始時刻
  };
  var Live2DCubismFramework26;
  ((Live2DCubismFramework42) => {
    Live2DCubismFramework42.CubismExpressionMotionManager = CubismExpressionMotionManager;
  })(Live2DCubismFramework26 || (Live2DCubismFramework26 = {}));

  // .trellis/workspace/lapp-runtime-src/src/renderer/WebSDK/Framework/src/motion/cubismmotioninternal.ts
  var CubismMotionCurveTarget = /* @__PURE__ */ ((CubismMotionCurveTarget2) => {
    CubismMotionCurveTarget2[CubismMotionCurveTarget2["CubismMotionCurveTarget_Model"] = 0] = "CubismMotionCurveTarget_Model";
    CubismMotionCurveTarget2[CubismMotionCurveTarget2["CubismMotionCurveTarget_Parameter"] = 1] = "CubismMotionCurveTarget_Parameter";
    CubismMotionCurveTarget2[CubismMotionCurveTarget2["CubismMotionCurveTarget_PartOpacity"] = 2] = "CubismMotionCurveTarget_PartOpacity";
    return CubismMotionCurveTarget2;
  })(CubismMotionCurveTarget || {});
  var CubismMotionSegmentType = /* @__PURE__ */ ((CubismMotionSegmentType2) => {
    CubismMotionSegmentType2[CubismMotionSegmentType2["CubismMotionSegmentType_Linear"] = 0] = "CubismMotionSegmentType_Linear";
    CubismMotionSegmentType2[CubismMotionSegmentType2["CubismMotionSegmentType_Bezier"] = 1] = "CubismMotionSegmentType_Bezier";
    CubismMotionSegmentType2[CubismMotionSegmentType2["CubismMotionSegmentType_Stepped"] = 2] = "CubismMotionSegmentType_Stepped";
    CubismMotionSegmentType2[CubismMotionSegmentType2["CubismMotionSegmentType_InverseStepped"] = 3] = "CubismMotionSegmentType_InverseStepped";
    return CubismMotionSegmentType2;
  })(CubismMotionSegmentType || {});
  var CubismMotionPoint = class {
    constructor() {
      __publicField(this, "time", 0);
      // 時間[秒]
      __publicField(this, "value", 0);
    }
    // 値
  };
  var CubismMotionSegment = class {
    /**
     * @brief コンストラクタ
     *
     * コンストラクタ。
     */
    constructor() {
      __publicField(this, "evaluate");
      // 使用する評価関数
      __publicField(this, "basePointIndex");
      // 最初のセグメントへのインデックス
      __publicField(this, "segmentType");
      this.evaluate = null;
      this.basePointIndex = 0;
      this.segmentType = 0;
    }
    // セグメントの種類
  };
  var CubismMotionCurve = class {
    constructor() {
      __publicField(this, "type");
      // カーブの種類
      __publicField(this, "id");
      // カーブのID
      __publicField(this, "segmentCount");
      // セグメントの個数
      __publicField(this, "baseSegmentIndex");
      // 最初のセグメントのインデックス
      __publicField(this, "fadeInTime");
      // フェードインにかかる時間[秒]
      __publicField(this, "fadeOutTime");
      this.type = 0 /* CubismMotionCurveTarget_Model */;
      this.segmentCount = 0;
      this.baseSegmentIndex = 0;
      this.fadeInTime = 0;
      this.fadeOutTime = 0;
    }
    // フェードアウトにかかる時間[秒]
  };
  var CubismMotionEvent = class {
    constructor() {
      __publicField(this, "fireTime", 0);
      __publicField(this, "value");
    }
  };
  var CubismMotionData = class {
    constructor() {
      __publicField(this, "duration");
      // モーションの長さ[秒]
      __publicField(this, "loop");
      // ループするかどうか
      __publicField(this, "curveCount");
      // カーブの個数
      __publicField(this, "eventCount");
      // UserDataの個数
      __publicField(this, "fps");
      // フレームレート
      __publicField(this, "curves");
      // カーブのリスト
      __publicField(this, "segments");
      // セグメントのリスト
      __publicField(this, "points");
      // ポイントのリスト
      __publicField(this, "events");
      this.duration = 0;
      this.loop = false;
      this.curveCount = 0;
      this.eventCount = 0;
      this.fps = 0;
      this.curves = new csmVector();
      this.segments = new csmVector();
      this.points = new csmVector();
      this.events = new csmVector();
    }
    // イベントのリスト
  };
  var Live2DCubismFramework27;
  ((Live2DCubismFramework42) => {
    Live2DCubismFramework42.CubismMotionCurve = CubismMotionCurve;
    Live2DCubismFramework42.CubismMotionCurveTarget = CubismMotionCurveTarget;
    Live2DCubismFramework42.CubismMotionData = CubismMotionData;
    Live2DCubismFramework42.CubismMotionEvent = CubismMotionEvent;
    Live2DCubismFramework42.CubismMotionPoint = CubismMotionPoint;
    Live2DCubismFramework42.CubismMotionSegment = CubismMotionSegment;
    Live2DCubismFramework42.CubismMotionSegmentType = CubismMotionSegmentType;
  })(Live2DCubismFramework27 || (Live2DCubismFramework27 = {}));

  // .trellis/workspace/lapp-runtime-src/src/renderer/WebSDK/Framework/src/motion/cubismmotionjson.ts
  var Meta = "Meta";
  var Duration = "Duration";
  var Loop = "Loop";
  var AreBeziersRestricted = "AreBeziersRestricted";
  var CurveCount = "CurveCount";
  var Fps = "Fps";
  var TotalSegmentCount = "TotalSegmentCount";
  var TotalPointCount = "TotalPointCount";
  var Curves = "Curves";
  var Target = "Target";
  var Id3 = "Id";
  var FadeInTime2 = "FadeInTime";
  var FadeOutTime2 = "FadeOutTime";
  var Segments = "Segments";
  var UserData2 = "UserData";
  var UserDataCount = "UserDataCount";
  var TotalUserDataSize = "TotalUserDataSize";
  var Time = "Time";
  var Value6 = "Value";
  var CubismMotionJson = class {
    /**
     * コンストラクタ
     * @param buffer motion3.jsonが読み込まれているバッファ
     * @param size バッファのサイズ
     */
    constructor(buffer, size) {
      __publicField(this, "_json");
      this._json = CubismJson.create(buffer, size);
    }
    /**
     * デストラクタ相当の処理
     */
    release() {
      CubismJson.delete(this._json);
    }
    /**
     * モーションの長さを取得する
     * @return モーションの長さ[秒]
     */
    getMotionDuration() {
      return this._json.getRoot().getValueByString(Meta).getValueByString(Duration).toFloat();
    }
    /**
     * モーションのループ情報の取得
     * @return true ループする
     * @return false ループしない
     */
    isMotionLoop() {
      return this._json.getRoot().getValueByString(Meta).getValueByString(Loop).toBoolean();
    }
    getEvaluationOptionFlag(flagType) {
      if (0 /* EvaluationOptionFlag_AreBeziersRistricted */ == flagType) {
        return this._json.getRoot().getValueByString(Meta).getValueByString(AreBeziersRestricted).toBoolean();
      }
      return false;
    }
    /**
     * モーションカーブの個数の取得
     * @return モーションカーブの個数
     */
    getMotionCurveCount() {
      return this._json.getRoot().getValueByString(Meta).getValueByString(CurveCount).toInt();
    }
    /**
     * モーションのフレームレートの取得
     * @return フレームレート[FPS]
     */
    getMotionFps() {
      return this._json.getRoot().getValueByString(Meta).getValueByString(Fps).toFloat();
    }
    /**
     * モーションのセグメントの総合計の取得
     * @return モーションのセグメントの取得
     */
    getMotionTotalSegmentCount() {
      return this._json.getRoot().getValueByString(Meta).getValueByString(TotalSegmentCount).toInt();
    }
    /**
     * モーションのカーブの制御店の総合計の取得
     * @return モーションのカーブの制御点の総合計
     */
    getMotionTotalPointCount() {
      return this._json.getRoot().getValueByString(Meta).getValueByString(TotalPointCount).toInt();
    }
    /**
     * モーションのフェードイン時間の存在
     * @return true 存在する
     * @return false 存在しない
     */
    isExistMotionFadeInTime() {
      return !this._json.getRoot().getValueByString(Meta).getValueByString(FadeInTime2).isNull();
    }
    /**
     * モーションのフェードアウト時間の存在
     * @return true 存在する
     * @return false 存在しない
     */
    isExistMotionFadeOutTime() {
      return !this._json.getRoot().getValueByString(Meta).getValueByString(FadeOutTime2).isNull();
    }
    /**
     * モーションのフェードイン時間の取得
     * @return フェードイン時間[秒]
     */
    getMotionFadeInTime() {
      return this._json.getRoot().getValueByString(Meta).getValueByString(FadeInTime2).toFloat();
    }
    /**
     * モーションのフェードアウト時間の取得
     * @return フェードアウト時間[秒]
     */
    getMotionFadeOutTime() {
      return this._json.getRoot().getValueByString(Meta).getValueByString(FadeOutTime2).toFloat();
    }
    /**
     * モーションのカーブの種類の取得
     * @param curveIndex カーブのインデックス
     * @return カーブの種類
     */
    getMotionCurveTarget(curveIndex) {
      return this._json.getRoot().getValueByString(Curves).getValueByIndex(curveIndex).getValueByString(Target).getRawString();
    }
    /**
     * モーションのカーブのIDの取得
     * @param curveIndex カーブのインデックス
     * @return カーブのID
     */
    getMotionCurveId(curveIndex) {
      return CubismFramework.getIdManager().getId(
        this._json.getRoot().getValueByString(Curves).getValueByIndex(curveIndex).getValueByString(Id3).getRawString()
      );
    }
    /**
     * モーションのカーブのフェードイン時間の存在
     * @param curveIndex カーブのインデックス
     * @return true 存在する
     * @return false 存在しない
     */
    isExistMotionCurveFadeInTime(curveIndex) {
      return !this._json.getRoot().getValueByString(Curves).getValueByIndex(curveIndex).getValueByString(FadeInTime2).isNull();
    }
    /**
     * モーションのカーブのフェードアウト時間の存在
     * @param curveIndex カーブのインデックス
     * @return true 存在する
     * @return false 存在しない
     */
    isExistMotionCurveFadeOutTime(curveIndex) {
      return !this._json.getRoot().getValueByString(Curves).getValueByIndex(curveIndex).getValueByString(FadeOutTime2).isNull();
    }
    /**
     * モーションのカーブのフェードイン時間の取得
     * @param curveIndex カーブのインデックス
     * @return フェードイン時間[秒]
     */
    getMotionCurveFadeInTime(curveIndex) {
      return this._json.getRoot().getValueByString(Curves).getValueByIndex(curveIndex).getValueByString(FadeInTime2).toFloat();
    }
    /**
     * モーションのカーブのフェードアウト時間の取得
     * @param curveIndex カーブのインデックス
     * @return フェードアウト時間[秒]
     */
    getMotionCurveFadeOutTime(curveIndex) {
      return this._json.getRoot().getValueByString(Curves).getValueByIndex(curveIndex).getValueByString(FadeOutTime2).toFloat();
    }
    /**
     * モーションのカーブのセグメントの個数を取得する
     * @param curveIndex カーブのインデックス
     * @return モーションのカーブのセグメントの個数
     */
    getMotionCurveSegmentCount(curveIndex) {
      return this._json.getRoot().getValueByString(Curves).getValueByIndex(curveIndex).getValueByString(Segments).getVector().getSize();
    }
    /**
     * モーションのカーブのセグメントの値の取得
     * @param curveIndex カーブのインデックス
     * @param segmentIndex セグメントのインデックス
     * @return セグメントの値
     */
    getMotionCurveSegment(curveIndex, segmentIndex) {
      return this._json.getRoot().getValueByString(Curves).getValueByIndex(curveIndex).getValueByString(Segments).getValueByIndex(segmentIndex).toFloat();
    }
    /**
     * イベントの個数の取得
     * @return イベントの個数
     */
    getEventCount() {
      return this._json.getRoot().getValueByString(Meta).getValueByString(UserDataCount).toInt();
    }
    /**
     *  イベントの総文字数の取得
     * @return イベントの総文字数
     */
    getTotalEventValueSize() {
      return this._json.getRoot().getValueByString(Meta).getValueByString(TotalUserDataSize).toInt();
    }
    /**
     * イベントの時間の取得
     * @param userDataIndex イベントのインデックス
     * @return イベントの時間[秒]
     */
    getEventTime(userDataIndex) {
      return this._json.getRoot().getValueByString(UserData2).getValueByIndex(userDataIndex).getValueByString(Time).toFloat();
    }
    /**
     * イベントの取得
     * @param userDataIndex イベントのインデックス
     * @return イベントの文字列
     */
    getEventValue(userDataIndex) {
      return new csmString(
        this._json.getRoot().getValueByString(UserData2).getValueByIndex(userDataIndex).getValueByString(Value6).getRawString()
      );
    }
    // motion3.jsonのデータ
  };
  var Live2DCubismFramework28;
  ((Live2DCubismFramework42) => {
    Live2DCubismFramework42.CubismMotionJson = CubismMotionJson;
  })(Live2DCubismFramework28 || (Live2DCubismFramework28 = {}));

  // .trellis/workspace/lapp-runtime-src/src/renderer/WebSDK/Framework/src/motion/cubismmotion.ts
  var EffectNameEyeBlink = "EyeBlink";
  var EffectNameLipSync = "LipSync";
  var TargetNameModel = "Model";
  var TargetNameParameter = "Parameter";
  var TargetNamePartOpacity = "PartOpacity";
  var IdNameOpacity = "Opacity";
  var UseOldBeziersCurveMotion = false;
  function lerpPoints(a, b, t) {
    const result = new CubismMotionPoint();
    result.time = a.time + (b.time - a.time) * t;
    result.value = a.value + (b.value - a.value) * t;
    return result;
  }
  function linearEvaluate(points, time) {
    let t = (time - points[0].time) / (points[1].time - points[0].time);
    if (t < 0) {
      t = 0;
    }
    return points[0].value + (points[1].value - points[0].value) * t;
  }
  function bezierEvaluate(points, time) {
    let t = (time - points[0].time) / (points[3].time - points[0].time);
    if (t < 0) {
      t = 0;
    }
    const p01 = lerpPoints(points[0], points[1], t);
    const p12 = lerpPoints(points[1], points[2], t);
    const p23 = lerpPoints(points[2], points[3], t);
    const p012 = lerpPoints(p01, p12, t);
    const p123 = lerpPoints(p12, p23, t);
    return lerpPoints(p012, p123, t).value;
  }
  function bezierEvaluateCardanoInterpretation(points, time) {
    const x = time;
    const x1 = points[0].time;
    const x2 = points[3].time;
    const cx1 = points[1].time;
    const cx2 = points[2].time;
    const a = x2 - 3 * cx2 + 3 * cx1 - x1;
    const b = 3 * cx2 - 6 * cx1 + 3 * x1;
    const c = 3 * cx1 - 3 * x1;
    const d = x1 - x;
    const t = CubismMath.cardanoAlgorithmForBezier(a, b, c, d);
    const p01 = lerpPoints(points[0], points[1], t);
    const p12 = lerpPoints(points[1], points[2], t);
    const p23 = lerpPoints(points[2], points[3], t);
    const p012 = lerpPoints(p01, p12, t);
    const p123 = lerpPoints(p12, p23, t);
    return lerpPoints(p012, p123, t).value;
  }
  function steppedEvaluate(points, time) {
    return points[0].value;
  }
  function inverseSteppedEvaluate(points, time) {
    return points[1].value;
  }
  function evaluateCurve(motionData, index, time) {
    const curve = motionData.curves.at(index);
    let target = -1;
    const totalSegmentCount = curve.baseSegmentIndex + curve.segmentCount;
    let pointPosition = 0;
    for (let i = curve.baseSegmentIndex; i < totalSegmentCount; ++i) {
      pointPosition = motionData.segments.at(i).basePointIndex + (motionData.segments.at(i).segmentType == 1 /* CubismMotionSegmentType_Bezier */ ? 3 : 1);
      if (motionData.points.at(pointPosition).time > time) {
        target = i;
        break;
      }
    }
    if (target == -1) {
      return motionData.points.at(pointPosition).value;
    }
    const segment = motionData.segments.at(target);
    return segment.evaluate(motionData.points.get(segment.basePointIndex), time);
  }
  var CubismMotion = class _CubismMotion extends ACubismMotion {
    /**
     * コンストラクタ
     */
    constructor() {
      super();
      __publicField(this, "_sourceFrameRate");
      // ロードしたファイルのFPS。記述が無ければデフォルト値15fpsとなる
      __publicField(this, "_loopDurationSeconds");
      // mtnファイルで定義される一連のモーションの長さ
      __publicField(this, "_isLoop");
      // ループするか?
      __publicField(this, "_isLoopFadeIn");
      // ループ時にフェードインが有効かどうかのフラグ。初期値では有効。
      __publicField(this, "_lastWeight");
      // 最後に設定された重み
      __publicField(this, "_motionData");
      // 実際のモーションデータ本体
      __publicField(this, "_eyeBlinkParameterIds");
      // 自動まばたきを適用するパラメータIDハンドルのリスト。  モデル（モデルセッティング）とパラメータを対応付ける。
      __publicField(this, "_lipSyncParameterIds");
      // リップシンクを適用するパラメータIDハンドルのリスト。  モデル（モデルセッティング）とパラメータを対応付ける。
      __publicField(this, "_modelCurveIdEyeBlink");
      // モデルが持つ自動まばたき用パラメータIDのハンドル。  モデルとモーションを対応付ける。
      __publicField(this, "_modelCurveIdLipSync");
      // モデルが持つリップシンク用パラメータIDのハンドル。  モデルとモーションを対応付ける。
      __publicField(this, "_modelCurveIdOpacity");
      // モデルが持つ不透明度用パラメータIDのハンドル。  モデルとモーションを対応付ける。
      __publicField(this, "_modelOpacity");
      this._sourceFrameRate = 30;
      this._loopDurationSeconds = -1;
      this._isLoop = false;
      this._isLoopFadeIn = true;
      this._lastWeight = 0;
      this._motionData = null;
      this._modelCurveIdEyeBlink = null;
      this._modelCurveIdLipSync = null;
      this._modelCurveIdOpacity = null;
      this._eyeBlinkParameterIds = null;
      this._lipSyncParameterIds = null;
      this._modelOpacity = 1;
    }
    /**
     * インスタンスを作成する
     *
     * @param buffer motion3.jsonが読み込まれているバッファ
     * @param size バッファのサイズ
     * @param onFinishedMotionHandler モーション再生終了時に呼び出されるコールバック関数
     * @return 作成されたインスタンス
     */
    static create(buffer, size, onFinishedMotionHandler) {
      const ret = new _CubismMotion();
      try {
        ret.parse(buffer, size);
        if (!ret._motionData) {
          CubismLogError("Failed to parse motion data - motion data is null");
          return null;
        }
        ret._sourceFrameRate = ret._motionData.fps;
        ret._loopDurationSeconds = ret._motionData.duration;
        ret._onFinishedMotion = onFinishedMotionHandler;
        return ret;
      } catch (error) {
        CubismLogError(`Failed to create motion: ${error}`);
        return null;
      }
    }
    /**
     * モデルのパラメータの更新の実行
     * @param model             対象のモデル
     * @param userTimeSeconds   現在の時刻[秒]
     * @param fadeWeight        モーションの重み
     * @param motionQueueEntry  CubismMotionQueueManagerで管理されているモーション
     */
    doUpdateParameters(model, userTimeSeconds, fadeWeight, motionQueueEntry) {
      if (this._modelCurveIdEyeBlink == null) {
        this._modelCurveIdEyeBlink = CubismFramework.getIdManager().getId(EffectNameEyeBlink);
      }
      if (this._modelCurveIdLipSync == null) {
        this._modelCurveIdLipSync = CubismFramework.getIdManager().getId(EffectNameLipSync);
      }
      if (this._modelCurveIdOpacity == null) {
        this._modelCurveIdOpacity = CubismFramework.getIdManager().getId(IdNameOpacity);
      }
      let timeOffsetSeconds = userTimeSeconds - motionQueueEntry.getStartTime();
      if (timeOffsetSeconds < 0) {
        timeOffsetSeconds = 0;
      }
      let lipSyncValue = Number.MAX_VALUE;
      let eyeBlinkValue = Number.MAX_VALUE;
      const maxTargetSize = 64;
      let lipSyncFlags = 0;
      let eyeBlinkFlags = 0;
      if (this._eyeBlinkParameterIds.getSize() > maxTargetSize) {
        CubismLogDebug(
          "too many eye blink targets : {0}",
          this._eyeBlinkParameterIds.getSize()
        );
      }
      if (this._lipSyncParameterIds.getSize() > maxTargetSize) {
        CubismLogDebug(
          "too many lip sync targets : {0}",
          this._lipSyncParameterIds.getSize()
        );
      }
      const tmpFadeIn = this._fadeInSeconds <= 0 ? 1 : CubismMath.getEasingSine(
        (userTimeSeconds - motionQueueEntry.getFadeInStartTime()) / this._fadeInSeconds
      );
      const tmpFadeOut = this._fadeOutSeconds <= 0 || motionQueueEntry.getEndTime() < 0 ? 1 : CubismMath.getEasingSine(
        (motionQueueEntry.getEndTime() - userTimeSeconds) / this._fadeOutSeconds
      );
      let value;
      let c, parameterIndex;
      let time = timeOffsetSeconds;
      if (this._isLoop) {
        while (time > this._motionData.duration) {
          time -= this._motionData.duration;
        }
      }
      const curves = this._motionData.curves;
      for (c = 0; c < this._motionData.curveCount && curves.at(c).type == 0 /* CubismMotionCurveTarget_Model */; ++c) {
        value = evaluateCurve(this._motionData, c, time);
        if (curves.at(c).id == this._modelCurveIdEyeBlink) {
          eyeBlinkValue = value;
        } else if (curves.at(c).id == this._modelCurveIdLipSync) {
          lipSyncValue = value;
        } else if (curves.at(c).id == this._modelCurveIdOpacity) {
          this._modelOpacity = value;
          model.setModelOapcity(this.getModelOpacityValue());
        }
      }
      let parameterMotionCurveCount = 0;
      for (; c < this._motionData.curveCount && curves.at(c).type == 1 /* CubismMotionCurveTarget_Parameter */; ++c) {
        parameterMotionCurveCount++;
        parameterIndex = model.getParameterIndex(curves.at(c).id);
        if (parameterIndex == -1) {
          continue;
        }
        const sourceValue = model.getParameterValueByIndex(parameterIndex);
        value = evaluateCurve(this._motionData, c, time);
        if (eyeBlinkValue != Number.MAX_VALUE) {
          for (let i = 0; i < this._eyeBlinkParameterIds.getSize() && i < maxTargetSize; ++i) {
            if (this._eyeBlinkParameterIds.at(i) == curves.at(c).id) {
              value *= eyeBlinkValue;
              eyeBlinkFlags |= 1 << i;
              break;
            }
          }
        }
        if (lipSyncValue != Number.MAX_VALUE) {
          for (let i = 0; i < this._lipSyncParameterIds.getSize() && i < maxTargetSize; ++i) {
            if (this._lipSyncParameterIds.at(i) == curves.at(c).id) {
              value += lipSyncValue;
              lipSyncFlags |= 1 << i;
              break;
            }
          }
        }
        let v;
        if (curves.at(c).fadeInTime < 0 && curves.at(c).fadeOutTime < 0) {
          v = sourceValue + (value - sourceValue) * fadeWeight;
        } else {
          let fin;
          let fout;
          if (curves.at(c).fadeInTime < 0) {
            fin = tmpFadeIn;
          } else {
            fin = curves.at(c).fadeInTime == 0 ? 1 : CubismMath.getEasingSine(
              (userTimeSeconds - motionQueueEntry.getFadeInStartTime()) / curves.at(c).fadeInTime
            );
          }
          if (curves.at(c).fadeOutTime < 0) {
            fout = tmpFadeOut;
          } else {
            fout = curves.at(c).fadeOutTime == 0 || motionQueueEntry.getEndTime() < 0 ? 1 : CubismMath.getEasingSine(
              (motionQueueEntry.getEndTime() - userTimeSeconds) / curves.at(c).fadeOutTime
            );
          }
          const paramWeight = this._weight * fin * fout;
          v = sourceValue + (value - sourceValue) * paramWeight;
        }
        model.setParameterValueByIndex(parameterIndex, v, 1);
      }
      {
        if (eyeBlinkValue != Number.MAX_VALUE) {
          for (let i = 0; i < this._eyeBlinkParameterIds.getSize() && i < maxTargetSize; ++i) {
            const sourceValue = model.getParameterValueById(
              this._eyeBlinkParameterIds.at(i)
            );
            if (eyeBlinkFlags >> i & 1) {
              continue;
            }
            const v = sourceValue + (eyeBlinkValue - sourceValue) * fadeWeight;
            model.setParameterValueById(this._eyeBlinkParameterIds.at(i), v);
          }
        }
        if (lipSyncValue != Number.MAX_VALUE) {
          for (let i = 0; i < this._lipSyncParameterIds.getSize() && i < maxTargetSize; ++i) {
            const sourceValue = model.getParameterValueById(
              this._lipSyncParameterIds.at(i)
            );
            if (lipSyncFlags >> i & 1) {
              continue;
            }
            const v = sourceValue + (lipSyncValue - sourceValue) * fadeWeight;
            model.setParameterValueById(this._lipSyncParameterIds.at(i), v);
          }
        }
      }
      for (; c < this._motionData.curveCount && curves.at(c).type == 2 /* CubismMotionCurveTarget_PartOpacity */; ++c) {
        parameterIndex = model.getParameterIndex(curves.at(c).id);
        if (parameterIndex == -1) {
          continue;
        }
        value = evaluateCurve(this._motionData, c, time);
        model.setParameterValueByIndex(parameterIndex, value);
      }
      if (timeOffsetSeconds >= this._motionData.duration) {
        if (this._isLoop) {
          motionQueueEntry.setStartTime(userTimeSeconds);
          if (this._isLoopFadeIn) {
            motionQueueEntry.setFadeInStartTime(userTimeSeconds);
          }
        } else {
          if (this._onFinishedMotion) {
            this._onFinishedMotion(this);
          }
          motionQueueEntry.setIsFinished(true);
        }
      }
      this._lastWeight = fadeWeight;
    }
    /**
     * ループ情報の設定
     * @param loop ループ情報
     */
    setIsLoop(loop) {
      this._isLoop = loop;
    }
    /**
     * ループ情報の取得
     * @return true ループする
     * @return false ループしない
     */
    isLoop() {
      return this._isLoop;
    }
    /**
     * ループ時のフェードイン情報の設定
     * @param loopFadeIn  ループ時のフェードイン情報
     */
    setIsLoopFadeIn(loopFadeIn) {
      this._isLoopFadeIn = loopFadeIn;
    }
    /**
     * ループ時のフェードイン情報の取得
     *
     * @return  true    する
     * @return  false   しない
     */
    isLoopFadeIn() {
      return this._isLoopFadeIn;
    }
    /**
     * モーションの長さを取得する。
     *
     * @return  モーションの長さ[秒]
     */
    getDuration() {
      return this._isLoop ? -1 : this._loopDurationSeconds;
    }
    /**
     * モーションのループ時の長さを取得する。
     *
     * @return  モーションのループ時の長さ[秒]
     */
    getLoopDuration() {
      return this._loopDurationSeconds;
    }
    /**
     * パラメータに対するフェードインの時間を設定する。
     *
     * @param parameterId     パラメータID
     * @param value           フェードインにかかる時間[秒]
     */
    setParameterFadeInTime(parameterId, value) {
      const curves = this._motionData.curves;
      for (let i = 0; i < this._motionData.curveCount; ++i) {
        if (parameterId == curves.at(i).id) {
          curves.at(i).fadeInTime = value;
          return;
        }
      }
    }
    /**
     * パラメータに対するフェードアウトの時間の設定
     * @param parameterId     パラメータID
     * @param value           フェードアウトにかかる時間[秒]
     */
    setParameterFadeOutTime(parameterId, value) {
      const curves = this._motionData.curves;
      for (let i = 0; i < this._motionData.curveCount; ++i) {
        if (parameterId == curves.at(i).id) {
          curves.at(i).fadeOutTime = value;
          return;
        }
      }
    }
    /**
     * パラメータに対するフェードインの時間の取得
     * @param    parameterId     パラメータID
     * @return   フェードインにかかる時間[秒]
     */
    getParameterFadeInTime(parameterId) {
      const curves = this._motionData.curves;
      for (let i = 0; i < this._motionData.curveCount; ++i) {
        if (parameterId == curves.at(i).id) {
          return curves.at(i).fadeInTime;
        }
      }
      return -1;
    }
    /**
     * パラメータに対するフェードアウトの時間を取得
     *
     * @param   parameterId     パラメータID
     * @return   フェードアウトにかかる時間[秒]
     */
    getParameterFadeOutTime(parameterId) {
      const curves = this._motionData.curves;
      for (let i = 0; i < this._motionData.curveCount; ++i) {
        if (parameterId == curves.at(i).id) {
          return curves.at(i).fadeOutTime;
        }
      }
      return -1;
    }
    /**
     * 自動エフェクトがかかっているパラメータIDリストの設定
     * @param eyeBlinkParameterIds    自動まばたきがかかっているパラメータIDのリスト
     * @param lipSyncParameterIds     リップシンクがかかっているパラメータIDのリスト
     */
    setEffectIds(eyeBlinkParameterIds, lipSyncParameterIds) {
      this._eyeBlinkParameterIds = eyeBlinkParameterIds;
      this._lipSyncParameterIds = lipSyncParameterIds;
    }
    /**
     * デストラクタ相当の処理
     */
    release() {
      this._motionData = void 0;
      this._motionData = null;
    }
    /**
     * motion3.jsonをパースする。
     *
     * @param motionJson  motion3.jsonが読み込まれているバッファ
     * @param size        バッファのサイズ
     */
    parse(motionJson, size) {
      this._motionData = new CubismMotionData();
      let json = new CubismMotionJson(motionJson, size);
      if (!json) {
        json.release();
        json = void 0;
        return;
      }
      this._motionData.duration = json.getMotionDuration();
      this._motionData.loop = json.isMotionLoop();
      this._motionData.curveCount = json.getMotionCurveCount();
      this._motionData.fps = json.getMotionFps();
      this._motionData.eventCount = json.getEventCount();
      const areBeziersRestructed = json.getEvaluationOptionFlag(
        0 /* EvaluationOptionFlag_AreBeziersRistricted */
      );
      if (json.isExistMotionFadeInTime()) {
        this._fadeInSeconds = json.getMotionFadeInTime() < 0 ? 1 : json.getMotionFadeInTime();
      } else {
        this._fadeInSeconds = 1;
      }
      if (json.isExistMotionFadeOutTime()) {
        this._fadeOutSeconds = json.getMotionFadeOutTime() < 0 ? 1 : json.getMotionFadeOutTime();
      } else {
        this._fadeOutSeconds = 1;
      }
      this._motionData.curves.updateSize(
        this._motionData.curveCount,
        CubismMotionCurve,
        true
      );
      let totalRequiredSegments = 0;
      let totalRequiredPoints = 0;
      for (let curveCount = 0; curveCount < this._motionData.curveCount; ++curveCount) {
        const segmentCount = json.getMotionCurveSegmentCount(curveCount);
        for (let segmentPos = 0; segmentPos < segmentCount; ) {
          totalRequiredSegments++;
          if (segmentPos == 0) {
            totalRequiredPoints += 1;
            segmentPos += 2;
          } else {
            const segmentType = json.getMotionCurveSegment(curveCount, segmentPos);
            switch (segmentType) {
              case 0 /* CubismMotionSegmentType_Linear */:
              case 2 /* CubismMotionSegmentType_Stepped */:
              case 3 /* CubismMotionSegmentType_InverseStepped */:
                totalRequiredPoints += 1;
                segmentPos += 3;
                break;
              case 1 /* CubismMotionSegmentType_Bezier */:
                totalRequiredPoints += 3;
                segmentPos += 7;
                break;
              default:
                segmentPos += 3;
                totalRequiredPoints += 1;
                break;
            }
          }
        }
      }
      this._motionData.segments.updateSize(
        totalRequiredSegments,
        CubismMotionSegment,
        true
      );
      this._motionData.points.updateSize(
        totalRequiredPoints,
        CubismMotionPoint,
        true
      );
      this._motionData.events.updateSize(
        this._motionData.eventCount,
        CubismMotionEvent,
        true
      );
      let totalPointCount = 0;
      let totalSegmentCount = 0;
      for (let curveCount = 0; curveCount < this._motionData.curveCount; ++curveCount) {
        if (json.getMotionCurveTarget(curveCount) == TargetNameModel) {
          this._motionData.curves.at(curveCount).type = 0 /* CubismMotionCurveTarget_Model */;
        } else if (json.getMotionCurveTarget(curveCount) == TargetNameParameter) {
          this._motionData.curves.at(curveCount).type = 1 /* CubismMotionCurveTarget_Parameter */;
        } else if (json.getMotionCurveTarget(curveCount) == TargetNamePartOpacity) {
          this._motionData.curves.at(curveCount).type = 2 /* CubismMotionCurveTarget_PartOpacity */;
        } else {
          CubismLogWarning(
            'Warning : Unable to get segment type from Curve! The number of "CurveCount" may be incorrect!'
          );
        }
        this._motionData.curves.at(curveCount).id = json.getMotionCurveId(curveCount);
        this._motionData.curves.at(curveCount).baseSegmentIndex = totalSegmentCount;
        this._motionData.curves.at(curveCount).fadeInTime = json.isExistMotionCurveFadeInTime(curveCount) ? json.getMotionCurveFadeInTime(curveCount) : -1;
        this._motionData.curves.at(curveCount).fadeOutTime = json.isExistMotionCurveFadeOutTime(curveCount) ? json.getMotionCurveFadeOutTime(curveCount) : -1;
        for (let segmentPosition = 0; segmentPosition < json.getMotionCurveSegmentCount(curveCount); ) {
          if (segmentPosition == 0) {
            this._motionData.segments.at(totalSegmentCount).basePointIndex = totalPointCount;
            this._motionData.points.at(totalPointCount).time = json.getMotionCurveSegment(curveCount, segmentPosition);
            this._motionData.points.at(totalPointCount).value = json.getMotionCurveSegment(curveCount, segmentPosition + 1);
            totalPointCount += 1;
            segmentPosition += 2;
          } else {
            this._motionData.segments.at(totalSegmentCount).basePointIndex = totalPointCount - 1;
          }
          const segment = json.getMotionCurveSegment(
            curveCount,
            segmentPosition
          );
          const segmentType = segment;
          switch (segmentType) {
            case 0 /* CubismMotionSegmentType_Linear */: {
              this._motionData.segments.at(totalSegmentCount).segmentType = 0 /* CubismMotionSegmentType_Linear */;
              this._motionData.segments.at(totalSegmentCount).evaluate = linearEvaluate;
              if (totalPointCount >= this._motionData.points.getSize()) {
                const newSize = Math.max(totalPointCount + 1, this._motionData.points.getSize() * 2);
                CubismLogWarning(`Expanding motion points array from ${this._motionData.points.getSize()} to ${newSize} for Linear segment`);
                this._motionData.points.updateSize(newSize, CubismMotionPoint, true);
              }
              this._motionData.points.at(totalPointCount).time = json.getMotionCurveSegment(curveCount, segmentPosition + 1);
              this._motionData.points.at(totalPointCount).value = json.getMotionCurveSegment(curveCount, segmentPosition + 2);
              totalPointCount += 1;
              segmentPosition += 3;
              break;
            }
            case 1 /* CubismMotionSegmentType_Bezier */: {
              this._motionData.segments.at(totalSegmentCount).segmentType = 1 /* CubismMotionSegmentType_Bezier */;
              if (areBeziersRestructed || UseOldBeziersCurveMotion) {
                this._motionData.segments.at(totalSegmentCount).evaluate = bezierEvaluate;
              } else {
                this._motionData.segments.at(totalSegmentCount).evaluate = bezierEvaluateCardanoInterpretation;
              }
              this._motionData.points.at(totalPointCount).time = json.getMotionCurveSegment(curveCount, segmentPosition + 1);
              this._motionData.points.at(totalPointCount).value = json.getMotionCurveSegment(curveCount, segmentPosition + 2);
              this._motionData.points.at(totalPointCount + 1).time = json.getMotionCurveSegment(curveCount, segmentPosition + 3);
              this._motionData.points.at(totalPointCount + 1).value = json.getMotionCurveSegment(curveCount, segmentPosition + 4);
              this._motionData.points.at(totalPointCount + 2).time = json.getMotionCurveSegment(curveCount, segmentPosition + 5);
              this._motionData.points.at(totalPointCount + 2).value = json.getMotionCurveSegment(curveCount, segmentPosition + 6);
              totalPointCount += 3;
              segmentPosition += 7;
              break;
            }
            case 2 /* CubismMotionSegmentType_Stepped */: {
              this._motionData.segments.at(totalSegmentCount).segmentType = 2 /* CubismMotionSegmentType_Stepped */;
              this._motionData.segments.at(totalSegmentCount).evaluate = steppedEvaluate;
              this._motionData.points.at(totalPointCount).time = json.getMotionCurveSegment(curveCount, segmentPosition + 1);
              this._motionData.points.at(totalPointCount).value = json.getMotionCurveSegment(curveCount, segmentPosition + 2);
              totalPointCount += 1;
              segmentPosition += 3;
              break;
            }
            case 3 /* CubismMotionSegmentType_InverseStepped */: {
              this._motionData.segments.at(totalSegmentCount).segmentType = 3 /* CubismMotionSegmentType_InverseStepped */;
              this._motionData.segments.at(totalSegmentCount).evaluate = inverseSteppedEvaluate;
              this._motionData.points.at(totalPointCount).time = json.getMotionCurveSegment(curveCount, segmentPosition + 1);
              this._motionData.points.at(totalPointCount).value = json.getMotionCurveSegment(curveCount, segmentPosition + 2);
              totalPointCount += 1;
              segmentPosition += 3;
              break;
            }
            default: {
              CSM_ASSERT(0);
              break;
            }
          }
          ++this._motionData.curves.at(curveCount).segmentCount;
          ++totalSegmentCount;
        }
      }
      for (let userdatacount = 0; userdatacount < json.getEventCount(); ++userdatacount) {
        this._motionData.events.at(userdatacount).fireTime = json.getEventTime(userdatacount);
        this._motionData.events.at(userdatacount).value = json.getEventValue(userdatacount);
      }
      json.release();
      json = void 0;
      json = null;
    }
    /**
     * モデルのパラメータ更新
     *
     * イベント発火のチェック。
     * 入力する時間は呼ばれるモーションタイミングを０とした秒数で行う。
     *
     * @param beforeCheckTimeSeconds   前回のイベントチェック時間[秒]
     * @param motionTimeSeconds        今回の再生時間[秒]
     */
    getFiredEvent(beforeCheckTimeSeconds, motionTimeSeconds) {
      this._firedEventValues.updateSize(0);
      for (let u = 0; u < this._motionData.eventCount; ++u) {
        if (this._motionData.events.at(u).fireTime > beforeCheckTimeSeconds && this._motionData.events.at(u).fireTime <= motionTimeSeconds) {
          this._firedEventValues.pushBack(
            new csmString(this._motionData.events.at(u).value.s)
          );
        }
      }
      return this._firedEventValues;
    }
    /**
     * 透明度のカーブが存在するかどうかを確認する
     *
     * @returns true  -> キーが存在する
     *          false -> キーが存在しない
     */
    isExistModelOpacity() {
      for (let i = 0; i < this._motionData.curveCount; i++) {
        const curve = this._motionData.curves.at(i);
        if (curve.type != 0 /* CubismMotionCurveTarget_Model */) {
          continue;
        }
        if (curve.id.getString().s.localeCompare(IdNameOpacity) == 0) {
          return true;
        }
      }
      return false;
    }
    /**
     * 透明度のカーブのインデックスを返す
     *
     * @returns success:透明度のカーブのインデックス
     */
    getModelOpacityIndex() {
      if (this.isExistModelOpacity()) {
        for (let i = 0; i < this._motionData.curveCount; i++) {
          const curve = this._motionData.curves.at(i);
          if (curve.type != 0 /* CubismMotionCurveTarget_Model */) {
            continue;
          }
          if (curve.id.getString().s.localeCompare(IdNameOpacity) == 0) {
            return i;
          }
        }
      }
      return -1;
    }
    /**
     * 透明度のIdを返す
     *
     * @param index モーションカーブのインデックス
     * @returns success:透明度のカーブのインデックス
     */
    getModelOpacityId(index) {
      if (index != -1) {
        const curve = this._motionData.curves.at(index);
        if (curve.type == 0 /* CubismMotionCurveTarget_Model */) {
          if (curve.id.getString().s.localeCompare(IdNameOpacity) == 0) {
            return CubismFramework.getIdManager().getId(curve.id.getString().s);
          }
        }
      }
      return null;
    }
    /**
     * 現在時間の透明度の値を返す
     *
     * @returns success:モーションの当該時間におけるOpacityの値
     */
    getModelOpacityValue() {
      return this._modelOpacity;
    }
    // モーションから取得した不透明度
  };
  var Live2DCubismFramework29;
  ((Live2DCubismFramework42) => {
    Live2DCubismFramework42.CubismMotion = CubismMotion;
  })(Live2DCubismFramework29 || (Live2DCubismFramework29 = {}));

  // .trellis/workspace/lapp-runtime-src/src/renderer/WebSDK/Framework/src/motion/cubismmotionmanager.ts
  var CubismMotionManager = class extends CubismMotionQueueManager {
    /**
     * コンストラクタ
     */
    constructor() {
      super();
      __publicField(this, "_currentPriority");
      // 現在再生中のモーションの優先度
      __publicField(this, "_reservePriority");
      this._currentPriority = 0;
      this._reservePriority = 0;
    }
    /**
     * 再生中のモーションの優先度の取得
     * @return  モーションの優先度
     */
    getCurrentPriority() {
      return this._currentPriority;
    }
    /**
     * 予約中のモーションの優先度を取得する。
     * @return  モーションの優先度
     */
    getReservePriority() {
      return this._reservePriority;
    }
    /**
     * 予約中のモーションの優先度を設定する。
     * @param   val     優先度
     */
    setReservePriority(val) {
      this._reservePriority = val;
    }
    /**
     * 優先度を設定してモーションを開始する。
     *
     * @param motion          モーション
     * @param autoDelete      再生が狩猟したモーションのインスタンスを削除するならtrue
     * @param priority        優先度
     * @return                開始したモーションの識別番号を返す。個別のモーションが終了したか否かを判定するIsFinished()の引数で使用する。開始できない時は「-1」
     */
    startMotionPriority(motion, autoDelete, priority) {
      if (priority == this._reservePriority) {
        this._reservePriority = 0;
      }
      this._currentPriority = priority;
      return super.startMotion(motion, autoDelete);
    }
    /**
     * モーションを更新して、モデルにパラメータ値を反映する。
     *
     * @param model   対象のモデル
     * @param deltaTimeSeconds    デルタ時間[秒]
     * @return  true    更新されている
     * @return  false   更新されていない
     */
    updateMotion(model, deltaTimeSeconds) {
      this._userTimeSeconds += deltaTimeSeconds;
      const updated = super.doUpdateMotion(model, this._userTimeSeconds);
      if (this.isFinished()) {
        this._currentPriority = 0;
      }
      return updated;
    }
    /**
     * モーションを予約する。
     *
     * @param   priority    優先度
     * @return  true    予約できた
     * @return  false   予約できなかった
     */
    reserveMotion(priority) {
      if (priority <= this._reservePriority || priority <= this._currentPriority) {
        return false;
      }
      this._reservePriority = priority;
      return true;
    }
    // 再生予定のモーションの優先度。再生中は0になる。モーションファイルを別スレッドで読み込むときの機能。
  };
  var Live2DCubismFramework30;
  ((Live2DCubismFramework42) => {
    Live2DCubismFramework42.CubismMotionManager = CubismMotionManager;
  })(Live2DCubismFramework30 || (Live2DCubismFramework30 = {}));

  // .trellis/workspace/lapp-runtime-src/src/renderer/WebSDK/Framework/src/physics/cubismphysicsinternal.ts
  var CubismPhysicsTargetType = /* @__PURE__ */ ((CubismPhysicsTargetType2) => {
    CubismPhysicsTargetType2[CubismPhysicsTargetType2["CubismPhysicsTargetType_Parameter"] = 0] = "CubismPhysicsTargetType_Parameter";
    return CubismPhysicsTargetType2;
  })(CubismPhysicsTargetType || {});
  var CubismPhysicsSource = /* @__PURE__ */ ((CubismPhysicsSource2) => {
    CubismPhysicsSource2[CubismPhysicsSource2["CubismPhysicsSource_X"] = 0] = "CubismPhysicsSource_X";
    CubismPhysicsSource2[CubismPhysicsSource2["CubismPhysicsSource_Y"] = 1] = "CubismPhysicsSource_Y";
    CubismPhysicsSource2[CubismPhysicsSource2["CubismPhysicsSource_Angle"] = 2] = "CubismPhysicsSource_Angle";
    return CubismPhysicsSource2;
  })(CubismPhysicsSource || {});
  var PhysicsJsonEffectiveForces = class {
    constructor() {
      __publicField(this, "gravity");
      // 重力
      __publicField(this, "wind");
      this.gravity = new CubismVector2(0, 0);
      this.wind = new CubismVector2(0, 0);
    }
    // 風
  };
  var CubismPhysicsParameter = class {
    constructor() {
      __publicField(this, "id");
      // パラメータ
      __publicField(this, "targetType");
    }
    // 適用先の種類
  };
  var CubismPhysicsNormalization = class {
    constructor() {
      __publicField(this, "minimum");
      // 最大値
      __publicField(this, "maximum");
      // 最小値
      __publicField(this, "defalut");
    }
    // デフォルト値
  };
  var CubismPhysicsParticle = class {
    constructor() {
      __publicField(this, "initialPosition");
      // 初期位置
      __publicField(this, "mobility");
      // 動きやすさ
      __publicField(this, "delay");
      // 遅れ
      __publicField(this, "acceleration");
      // 加速度
      __publicField(this, "radius");
      // 距離
      __publicField(this, "position");
      // 現在の位置
      __publicField(this, "lastPosition");
      // 最後の位置
      __publicField(this, "lastGravity");
      // 最後の重力
      __publicField(this, "force");
      // 現在かかっている力
      __publicField(this, "velocity");
      this.initialPosition = new CubismVector2(0, 0);
      this.position = new CubismVector2(0, 0);
      this.lastPosition = new CubismVector2(0, 0);
      this.lastGravity = new CubismVector2(0, 0);
      this.force = new CubismVector2(0, 0);
      this.velocity = new CubismVector2(0, 0);
    }
    // 現在の速度
  };
  var CubismPhysicsSubRig = class {
    constructor() {
      __publicField(this, "inputCount");
      // 入力の個数
      __publicField(this, "outputCount");
      // 出力の個数
      __publicField(this, "particleCount");
      // 物理点の個数
      __publicField(this, "baseInputIndex");
      // 入力の最初のインデックス
      __publicField(this, "baseOutputIndex");
      // 出力の最初のインデックス
      __publicField(this, "baseParticleIndex");
      // 物理点の最初のインデックス
      __publicField(this, "normalizationPosition");
      // 正規化された位置
      __publicField(this, "normalizationAngle");
      this.normalizationPosition = new CubismPhysicsNormalization();
      this.normalizationAngle = new CubismPhysicsNormalization();
    }
    // 正規化された角度
  };
  var CubismPhysicsInput = class {
    constructor() {
      __publicField(this, "source");
      // 入力元のパラメータ
      __publicField(this, "sourceParameterIndex");
      // 入力元のパラメータのインデックス
      __publicField(this, "weight");
      // 重み
      __publicField(this, "type");
      // 入力の種類
      __publicField(this, "reflect");
      // 値が反転されているかどうか
      __publicField(this, "getNormalizedParameterValue");
      this.source = new CubismPhysicsParameter();
    }
    // 正規化されたパラメータ値の取得関数
  };
  var CubismPhysicsOutput = class {
    constructor() {
      __publicField(this, "destination");
      // 出力先のパラメータ
      __publicField(this, "destinationParameterIndex");
      // 出力先のパラメータのインデックス
      __publicField(this, "vertexIndex");
      // 振り子のインデックス
      __publicField(this, "translationScale");
      // 移動値のスケール
      __publicField(this, "angleScale");
      // 角度のスケール
      __publicField(this, "weight");
      // 重み
      __publicField(this, "type");
      // 出力の種類
      __publicField(this, "reflect");
      // 値が反転されているかどうか
      __publicField(this, "valueBelowMinimum");
      // 最小値を下回った時の値
      __publicField(this, "valueExceededMaximum");
      // 最大値をこえた時の値
      __publicField(this, "getValue");
      // 物理演算の値の取得関数
      __publicField(this, "getScale");
      this.destination = new CubismPhysicsParameter();
      this.translationScale = new CubismVector2(0, 0);
    }
    // 物理演算のスケール値の取得関数
  };
  var CubismPhysicsRig = class {
    constructor() {
      __publicField(this, "subRigCount");
      // 物理演算の物理点の個数
      __publicField(this, "settings");
      // 物理演算の物理点の管理のリスト
      __publicField(this, "inputs");
      // 物理演算の入力のリスト
      __publicField(this, "outputs");
      // 物理演算の出力のリスト
      __publicField(this, "particles");
      // 物理演算の物理点のリスト
      __publicField(this, "gravity");
      // 重力
      __publicField(this, "wind");
      // 風
      __publicField(this, "fps");
      this.settings = new csmVector();
      this.inputs = new csmVector();
      this.outputs = new csmVector();
      this.particles = new csmVector();
      this.gravity = new CubismVector2(0, 0);
      this.wind = new CubismVector2(0, 0);
      this.fps = 0;
    }
    //物理演算動作FPS
  };
  var Live2DCubismFramework31;
  ((Live2DCubismFramework42) => {
    Live2DCubismFramework42.CubismPhysicsInput = CubismPhysicsInput;
    Live2DCubismFramework42.CubismPhysicsNormalization = CubismPhysicsNormalization;
    Live2DCubismFramework42.CubismPhysicsOutput = CubismPhysicsOutput;
    Live2DCubismFramework42.CubismPhysicsParameter = CubismPhysicsParameter;
    Live2DCubismFramework42.CubismPhysicsParticle = CubismPhysicsParticle;
    Live2DCubismFramework42.CubismPhysicsRig = CubismPhysicsRig;
    Live2DCubismFramework42.CubismPhysicsSource = CubismPhysicsSource;
    Live2DCubismFramework42.CubismPhysicsSubRig = CubismPhysicsSubRig;
    Live2DCubismFramework42.CubismPhysicsTargetType = CubismPhysicsTargetType;
    Live2DCubismFramework42.PhysicsJsonEffectiveForces = PhysicsJsonEffectiveForces;
  })(Live2DCubismFramework31 || (Live2DCubismFramework31 = {}));

  // .trellis/workspace/lapp-runtime-src/src/renderer/WebSDK/Framework/src/physics/cubismphysicsjson.ts
  var Position = "Position";
  var X = "X";
  var Y = "Y";
  var Angle = "Angle";
  var Type = "Type";
  var Id4 = "Id";
  var Meta2 = "Meta";
  var EffectiveForces = "EffectiveForces";
  var TotalInputCount = "TotalInputCount";
  var TotalOutputCount = "TotalOutputCount";
  var PhysicsSettingCount = "PhysicsSettingCount";
  var Gravity = "Gravity";
  var Wind = "Wind";
  var VertexCount = "VertexCount";
  var Fps2 = "Fps";
  var PhysicsSettings = "PhysicsSettings";
  var Normalization = "Normalization";
  var Minimum = "Minimum";
  var Maximum = "Maximum";
  var Default = "Default";
  var Reflect2 = "Reflect";
  var Weight = "Weight";
  var Input = "Input";
  var Source = "Source";
  var Output = "Output";
  var Scale = "Scale";
  var VertexIndex = "VertexIndex";
  var Destination = "Destination";
  var Vertices = "Vertices";
  var Mobility = "Mobility";
  var Delay = "Delay";
  var Radius = "Radius";
  var Acceleration = "Acceleration";
  var CubismPhysicsJson = class {
    /**
     * コンストラクタ
     * @param buffer physics3.jsonが読み込まれているバッファ
     * @param size バッファのサイズ
     */
    constructor(buffer, size) {
      __publicField(this, "_json");
      this._json = CubismJson.create(buffer, size);
    }
    /**
     * デストラクタ相当の処理
     */
    release() {
      CubismJson.delete(this._json);
    }
    /**
     * 重力の取得
     * @return 重力
     */
    getGravity() {
      const ret = new CubismVector2(0, 0);
      ret.x = this._json.getRoot().getValueByString(Meta2).getValueByString(EffectiveForces).getValueByString(Gravity).getValueByString(X).toFloat();
      ret.y = this._json.getRoot().getValueByString(Meta2).getValueByString(EffectiveForces).getValueByString(Gravity).getValueByString(Y).toFloat();
      return ret;
    }
    /**
     * 風の取得
     * @return 風
     */
    getWind() {
      const ret = new CubismVector2(0, 0);
      ret.x = this._json.getRoot().getValueByString(Meta2).getValueByString(EffectiveForces).getValueByString(Wind).getValueByString(X).toFloat();
      ret.y = this._json.getRoot().getValueByString(Meta2).getValueByString(EffectiveForces).getValueByString(Wind).getValueByString(Y).toFloat();
      return ret;
    }
    /**
     * 物理演算設定FPSの取得
     * @return 物理演算設定FPS
     */
    getFps() {
      return this._json.getRoot().getValueByString(Meta2).getValueByString(Fps2).toFloat(0);
    }
    /**
     * 物理店の管理の個数の取得
     * @return 物理店の管理の個数
     */
    getSubRigCount() {
      return this._json.getRoot().getValueByString(Meta2).getValueByString(PhysicsSettingCount).toInt();
    }
    /**
     * 入力の総合計の取得
     * @return 入力の総合計
     */
    getTotalInputCount() {
      return this._json.getRoot().getValueByString(Meta2).getValueByString(TotalInputCount).toInt();
    }
    /**
     * 出力の総合計の取得
     * @return 出力の総合計
     */
    getTotalOutputCount() {
      return this._json.getRoot().getValueByString(Meta2).getValueByString(TotalOutputCount).toInt();
    }
    /**
     * 物理点の個数の取得
     * @return 物理点の個数
     */
    getVertexCount() {
      return this._json.getRoot().getValueByString(Meta2).getValueByString(VertexCount).toInt();
    }
    /**
     * 正規化された位置の最小値の取得
     * @param physicsSettingIndex 物理演算の設定のインデックス
     * @return 正規化された位置の最小値
     */
    getNormalizationPositionMinimumValue(physicsSettingIndex) {
      return this._json.getRoot().getValueByString(PhysicsSettings).getValueByIndex(physicsSettingIndex).getValueByString(Normalization).getValueByString(Position).getValueByString(Minimum).toFloat();
    }
    /**
     * 正規化された位置の最大値の取得
     * @param physicsSettingIndex 物理演算の設定のインデックス
     * @return 正規化された位置の最大値
     */
    getNormalizationPositionMaximumValue(physicsSettingIndex) {
      return this._json.getRoot().getValueByString(PhysicsSettings).getValueByIndex(physicsSettingIndex).getValueByString(Normalization).getValueByString(Position).getValueByString(Maximum).toFloat();
    }
    /**
     * 正規化された位置のデフォルト値の取得
     * @param physicsSettingIndex 物理演算の設定のインデックス
     * @return 正規化された位置のデフォルト値
     */
    getNormalizationPositionDefaultValue(physicsSettingIndex) {
      return this._json.getRoot().getValueByString(PhysicsSettings).getValueByIndex(physicsSettingIndex).getValueByString(Normalization).getValueByString(Position).getValueByString(Default).toFloat();
    }
    /**
     * 正規化された角度の最小値の取得
     * @param physicsSettingIndex 物理演算の設定のインデックス
     * @return 正規化された角度の最小値
     */
    getNormalizationAngleMinimumValue(physicsSettingIndex) {
      return this._json.getRoot().getValueByString(PhysicsSettings).getValueByIndex(physicsSettingIndex).getValueByString(Normalization).getValueByString(Angle).getValueByString(Minimum).toFloat();
    }
    /**
     * 正規化された角度の最大値の取得
     * @param physicsSettingIndex
     * @return 正規化された角度の最大値
     */
    getNormalizationAngleMaximumValue(physicsSettingIndex) {
      return this._json.getRoot().getValueByString(PhysicsSettings).getValueByIndex(physicsSettingIndex).getValueByString(Normalization).getValueByString(Angle).getValueByString(Maximum).toFloat();
    }
    /**
     * 正規化された角度のデフォルト値の取得
     * @param physicsSettingIndex 物理演算の設定のインデックス
     * @return 正規化された角度のデフォルト値
     */
    getNormalizationAngleDefaultValue(physicsSettingIndex) {
      return this._json.getRoot().getValueByString(PhysicsSettings).getValueByIndex(physicsSettingIndex).getValueByString(Normalization).getValueByString(Angle).getValueByString(Default).toFloat();
    }
    /**
     * 入力の個数の取得
     * @param physicsSettingIndex 物理演算の設定のインデックス
     * @return 入力の個数
     */
    getInputCount(physicsSettingIndex) {
      return this._json.getRoot().getValueByString(PhysicsSettings).getValueByIndex(physicsSettingIndex).getValueByString(Input).getVector().getSize();
    }
    /**
     * 入力の重みの取得
     * @param physicsSettingIndex 物理演算の設定のインデックス
     * @param inputIndex 入力のインデックス
     * @return 入力の重み
     */
    getInputWeight(physicsSettingIndex, inputIndex) {
      return this._json.getRoot().getValueByString(PhysicsSettings).getValueByIndex(physicsSettingIndex).getValueByString(Input).getValueByIndex(inputIndex).getValueByString(Weight).toFloat();
    }
    /**
     * 入力の反転の取得
     * @param physicsSettingIndex 物理演算の設定のインデックス
     * @param inputIndex 入力のインデックス
     * @return 入力の反転
     */
    getInputReflect(physicsSettingIndex, inputIndex) {
      return this._json.getRoot().getValueByString(PhysicsSettings).getValueByIndex(physicsSettingIndex).getValueByString(Input).getValueByIndex(inputIndex).getValueByString(Reflect2).toBoolean();
    }
    /**
     * 入力の種類の取得
     * @param physicsSettingIndex 物理演算の設定のインデックス
     * @param inputIndex 入力のインデックス
     * @return 入力の種類
     */
    getInputType(physicsSettingIndex, inputIndex) {
      return this._json.getRoot().getValueByString(PhysicsSettings).getValueByIndex(physicsSettingIndex).getValueByString(Input).getValueByIndex(inputIndex).getValueByString(Type).getRawString();
    }
    /**
     * 入力元のIDの取得
     * @param physicsSettingIndex 物理演算の設定のインデックス
     * @param inputIndex 入力のインデックス
     * @return 入力元のID
     */
    getInputSourceId(physicsSettingIndex, inputIndex) {
      return CubismFramework.getIdManager().getId(
        this._json.getRoot().getValueByString(PhysicsSettings).getValueByIndex(physicsSettingIndex).getValueByString(Input).getValueByIndex(inputIndex).getValueByString(Source).getValueByString(Id4).getRawString()
      );
    }
    /**
     * 出力の個数の取得
     * @param physicsSettingIndex 物理演算の設定のインデックス
     * @return 出力の個数
     */
    getOutputCount(physicsSettingIndex) {
      return this._json.getRoot().getValueByString(PhysicsSettings).getValueByIndex(physicsSettingIndex).getValueByString(Output).getVector().getSize();
    }
    /**
     * 出力の物理点のインデックスの取得
     * @param physicsSettingIndex 物理演算の設定のインデックス
     * @param outputIndex 出力のインデックス
     * @return 出力の物理点のインデックス
     */
    getOutputVertexIndex(physicsSettingIndex, outputIndex) {
      return this._json.getRoot().getValueByString(PhysicsSettings).getValueByIndex(physicsSettingIndex).getValueByString(Output).getValueByIndex(outputIndex).getValueByString(VertexIndex).toInt();
    }
    /**
     * 出力の角度のスケールを取得する
     * @param physicsSettingIndex 物理演算の設定のインデックス
     * @param outputIndex 出力のインデックス
     * @return 出力の角度のスケール
     */
    getOutputAngleScale(physicsSettingIndex, outputIndex) {
      return this._json.getRoot().getValueByString(PhysicsSettings).getValueByIndex(physicsSettingIndex).getValueByString(Output).getValueByIndex(outputIndex).getValueByString(Scale).toFloat();
    }
    /**
     * 出力の重みの取得
     * @param physicsSettingIndex 物理演算の設定のインデックス
     * @param outputIndex 出力のインデックス
     * @return 出力の重み
     */
    getOutputWeight(physicsSettingIndex, outputIndex) {
      return this._json.getRoot().getValueByString(PhysicsSettings).getValueByIndex(physicsSettingIndex).getValueByString(Output).getValueByIndex(outputIndex).getValueByString(Weight).toFloat();
    }
    /**
     * 出力先のIDの取得
     * @param physicsSettingIndex 物理演算の設定のインデックス
     * @param outputIndex 出力のインデックス
     * @return 出力先のID
     */
    getOutputDestinationId(physicsSettingIndex, outputIndex) {
      return CubismFramework.getIdManager().getId(
        this._json.getRoot().getValueByString(PhysicsSettings).getValueByIndex(physicsSettingIndex).getValueByString(Output).getValueByIndex(outputIndex).getValueByString(Destination).getValueByString(Id4).getRawString()
      );
    }
    /**
     * 出力の種類の取得
     * @param physicsSettingIndex 物理演算の設定のインデックス
     * @param outputIndex 出力のインデックス
     * @return 出力の種類
     */
    getOutputType(physicsSettingIndex, outputIndex) {
      return this._json.getRoot().getValueByString(PhysicsSettings).getValueByIndex(physicsSettingIndex).getValueByString(Output).getValueByIndex(outputIndex).getValueByString(Type).getRawString();
    }
    /**
     * 出力の反転の取得
     * @param physicsSettingIndex 物理演算のインデックス
     * @param outputIndex 出力のインデックス
     * @return 出力の反転
     */
    getOutputReflect(physicsSettingIndex, outputIndex) {
      return this._json.getRoot().getValueByString(PhysicsSettings).getValueByIndex(physicsSettingIndex).getValueByString(Output).getValueByIndex(outputIndex).getValueByString(Reflect2).toBoolean();
    }
    /**
     * 物理点の個数の取得
     * @param physicsSettingIndex 物理演算男設定のインデックス
     * @return 物理点の個数
     */
    getParticleCount(physicsSettingIndex) {
      return this._json.getRoot().getValueByString(PhysicsSettings).getValueByIndex(physicsSettingIndex).getValueByString(Vertices).getVector().getSize();
    }
    /**
     * 物理点の動きやすさの取得
     * @param physicsSettingIndex 物理演算の設定のインデックス
     * @param vertexIndex 物理点のインデックス
     * @return 物理点の動きやすさ
     */
    getParticleMobility(physicsSettingIndex, vertexIndex) {
      return this._json.getRoot().getValueByString(PhysicsSettings).getValueByIndex(physicsSettingIndex).getValueByString(Vertices).getValueByIndex(vertexIndex).getValueByString(Mobility).toFloat();
    }
    /**
     * 物理点の遅れの取得
     * @param physicsSettingIndex 物理演算の設定のインデックス
     * @param vertexIndex 物理点のインデックス
     * @return 物理点の遅れ
     */
    getParticleDelay(physicsSettingIndex, vertexIndex) {
      return this._json.getRoot().getValueByString(PhysicsSettings).getValueByIndex(physicsSettingIndex).getValueByString(Vertices).getValueByIndex(vertexIndex).getValueByString(Delay).toFloat();
    }
    /**
     * 物理点の加速度の取得
     * @param physicsSettingIndex 物理演算の設定
     * @param vertexIndex 物理点のインデックス
     * @return 物理点の加速度
     */
    getParticleAcceleration(physicsSettingIndex, vertexIndex) {
      return this._json.getRoot().getValueByString(PhysicsSettings).getValueByIndex(physicsSettingIndex).getValueByString(Vertices).getValueByIndex(vertexIndex).getValueByString(Acceleration).toFloat();
    }
    /**
     * 物理点の距離の取得
     * @param physicsSettingIndex 物理演算の設定のインデックス
     * @param vertexIndex 物理点のインデックス
     * @return 物理点の距離
     */
    getParticleRadius(physicsSettingIndex, vertexIndex) {
      return this._json.getRoot().getValueByString(PhysicsSettings).getValueByIndex(physicsSettingIndex).getValueByString(Vertices).getValueByIndex(vertexIndex).getValueByString(Radius).toFloat();
    }
    /**
     * 物理点の位置の取得
     * @param physicsSettingIndex 物理演算の設定のインデックス
     * @param vertexInde 物理点のインデックス
     * @return 物理点の位置
     */
    getParticlePosition(physicsSettingIndex, vertexIndex) {
      const ret = new CubismVector2(0, 0);
      ret.x = this._json.getRoot().getValueByString(PhysicsSettings).getValueByIndex(physicsSettingIndex).getValueByString(Vertices).getValueByIndex(vertexIndex).getValueByString(Position).getValueByString(X).toFloat();
      ret.y = this._json.getRoot().getValueByString(PhysicsSettings).getValueByIndex(physicsSettingIndex).getValueByString(Vertices).getValueByIndex(vertexIndex).getValueByString(Position).getValueByString(Y).toFloat();
      return ret;
    }
    // physics3.jsonデータ
  };
  var Live2DCubismFramework32;
  ((Live2DCubismFramework42) => {
    Live2DCubismFramework42.CubismPhysicsJson = CubismPhysicsJson;
  })(Live2DCubismFramework32 || (Live2DCubismFramework32 = {}));

  // .trellis/workspace/lapp-runtime-src/src/renderer/WebSDK/Framework/src/physics/cubismphysics.ts
  var PhysicsTypeTagX = "X";
  var PhysicsTypeTagY = "Y";
  var PhysicsTypeTagAngle = "Angle";
  var AirResistance = 5;
  var MaximumWeight = 100;
  var MovementThreshold = 1e-3;
  var MaxDeltaTime = 5;
  var CubismPhysics = class _CubismPhysics {
    /**
     * コンストラクタ
     */
    constructor() {
      __publicField(this, "_physicsRig");
      // 物理演算のデータ
      __publicField(this, "_options");
      // オプション
      __publicField(this, "_currentRigOutputs");
      ///< 最新の振り子計算の結果
      __publicField(this, "_previousRigOutputs");
      ///< 一つ前の振り子計算の結果
      __publicField(this, "_currentRemainTime");
      ///< 物理演算が処理していない時間
      __publicField(this, "_parameterCaches");
      ///< Evaluateで利用するパラメータのキャッシュ
      __publicField(this, "_parameterInputCaches");
      this._physicsRig = null;
      this._options = new Options();
      this._options.gravity.y = -1;
      this._options.gravity.x = 0;
      this._options.wind.x = 0;
      this._options.wind.y = 0;
      this._currentRigOutputs = new csmVector();
      this._previousRigOutputs = new csmVector();
      this._currentRemainTime = 0;
      this._parameterCaches = null;
      this._parameterInputCaches = null;
    }
    /**
     * インスタンスの作成
     * @param buffer    physics3.jsonが読み込まれているバッファ
     * @param size      バッファのサイズ
     * @return 作成されたインスタンス
     */
    static create(buffer, size) {
      const ret = new _CubismPhysics();
      ret.parse(buffer, size);
      ret._physicsRig.gravity.y = 0;
      return ret;
    }
    /**
     * インスタンスを破棄する
     * @param physics 破棄するインスタンス
     */
    static delete(physics) {
      if (physics != null) {
        physics.release();
        physics = null;
      }
    }
    /**
     * physics3.jsonをパースする。
     * @param physicsJson physics3.jsonが読み込まれているバッファ
     * @param size バッファのサイズ
     */
    parse(physicsJson, size) {
      this._physicsRig = new CubismPhysicsRig();
      let json = new CubismPhysicsJson(physicsJson, size);
      this._physicsRig.gravity = json.getGravity();
      this._physicsRig.wind = json.getWind();
      this._physicsRig.subRigCount = json.getSubRigCount();
      this._physicsRig.fps = json.getFps();
      this._physicsRig.settings.updateSize(
        this._physicsRig.subRigCount,
        CubismPhysicsSubRig,
        true
      );
      this._physicsRig.inputs.updateSize(
        json.getTotalInputCount(),
        CubismPhysicsInput,
        true
      );
      this._physicsRig.outputs.updateSize(
        json.getTotalOutputCount(),
        CubismPhysicsOutput,
        true
      );
      this._physicsRig.particles.updateSize(
        json.getVertexCount(),
        CubismPhysicsParticle,
        true
      );
      this._currentRigOutputs.clear();
      this._previousRigOutputs.clear();
      let inputIndex = 0, outputIndex = 0, particleIndex = 0;
      for (let i = 0; i < this._physicsRig.settings.getSize(); ++i) {
        this._physicsRig.settings.at(i).normalizationPosition.minimum = json.getNormalizationPositionMinimumValue(i);
        this._physicsRig.settings.at(i).normalizationPosition.maximum = json.getNormalizationPositionMaximumValue(i);
        this._physicsRig.settings.at(i).normalizationPosition.defalut = json.getNormalizationPositionDefaultValue(i);
        this._physicsRig.settings.at(i).normalizationAngle.minimum = json.getNormalizationAngleMinimumValue(i);
        this._physicsRig.settings.at(i).normalizationAngle.maximum = json.getNormalizationAngleMaximumValue(i);
        this._physicsRig.settings.at(i).normalizationAngle.defalut = json.getNormalizationAngleDefaultValue(i);
        this._physicsRig.settings.at(i).inputCount = json.getInputCount(i);
        this._physicsRig.settings.at(i).baseInputIndex = inputIndex;
        for (let j = 0; j < this._physicsRig.settings.at(i).inputCount; ++j) {
          this._physicsRig.inputs.at(inputIndex + j).sourceParameterIndex = -1;
          this._physicsRig.inputs.at(inputIndex + j).weight = json.getInputWeight(
            i,
            j
          );
          this._physicsRig.inputs.at(inputIndex + j).reflect = json.getInputReflect(i, j);
          if (json.getInputType(i, j) == PhysicsTypeTagX) {
            this._physicsRig.inputs.at(inputIndex + j).type = 0 /* CubismPhysicsSource_X */;
            this._physicsRig.inputs.at(
              inputIndex + j
            ).getNormalizedParameterValue = getInputTranslationXFromNormalizedParameterValue;
          } else if (json.getInputType(i, j) == PhysicsTypeTagY) {
            this._physicsRig.inputs.at(inputIndex + j).type = 1 /* CubismPhysicsSource_Y */;
            this._physicsRig.inputs.at(
              inputIndex + j
            ).getNormalizedParameterValue = getInputTranslationYFromNormalizedParamterValue;
          } else if (json.getInputType(i, j) == PhysicsTypeTagAngle) {
            this._physicsRig.inputs.at(inputIndex + j).type = 2 /* CubismPhysicsSource_Angle */;
            this._physicsRig.inputs.at(
              inputIndex + j
            ).getNormalizedParameterValue = getInputAngleFromNormalizedParameterValue;
          }
          this._physicsRig.inputs.at(inputIndex + j).source.targetType = 0 /* CubismPhysicsTargetType_Parameter */;
          this._physicsRig.inputs.at(inputIndex + j).source.id = json.getInputSourceId(i, j);
        }
        inputIndex += this._physicsRig.settings.at(i).inputCount;
        this._physicsRig.settings.at(i).outputCount = json.getOutputCount(i);
        this._physicsRig.settings.at(i).baseOutputIndex = outputIndex;
        const currentRigOutput = new PhysicsOutput();
        currentRigOutput.outputs.resize(
          this._physicsRig.settings.at(i).outputCount
        );
        const previousRigOutput = new PhysicsOutput();
        previousRigOutput.outputs.resize(
          this._physicsRig.settings.at(i).outputCount
        );
        for (let j = 0; j < this._physicsRig.settings.at(i).outputCount; ++j) {
          currentRigOutput.outputs.set(j, 0);
          previousRigOutput.outputs.set(j, 0);
          this._physicsRig.outputs.at(outputIndex + j).destinationParameterIndex = -1;
          this._physicsRig.outputs.at(outputIndex + j).vertexIndex = json.getOutputVertexIndex(i, j);
          this._physicsRig.outputs.at(outputIndex + j).angleScale = json.getOutputAngleScale(i, j);
          this._physicsRig.outputs.at(outputIndex + j).weight = json.getOutputWeight(i, j);
          this._physicsRig.outputs.at(outputIndex + j).destination.targetType = 0 /* CubismPhysicsTargetType_Parameter */;
          this._physicsRig.outputs.at(outputIndex + j).destination.id = json.getOutputDestinationId(i, j);
          if (json.getOutputType(i, j) == PhysicsTypeTagX) {
            this._physicsRig.outputs.at(outputIndex + j).type = 0 /* CubismPhysicsSource_X */;
            this._physicsRig.outputs.at(outputIndex + j).getValue = getOutputTranslationX;
            this._physicsRig.outputs.at(outputIndex + j).getScale = getOutputScaleTranslationX;
          } else if (json.getOutputType(i, j) == PhysicsTypeTagY) {
            this._physicsRig.outputs.at(outputIndex + j).type = 1 /* CubismPhysicsSource_Y */;
            this._physicsRig.outputs.at(outputIndex + j).getValue = getOutputTranslationY;
            this._physicsRig.outputs.at(outputIndex + j).getScale = getOutputScaleTranslationY;
          } else if (json.getOutputType(i, j) == PhysicsTypeTagAngle) {
            this._physicsRig.outputs.at(outputIndex + j).type = 2 /* CubismPhysicsSource_Angle */;
            this._physicsRig.outputs.at(outputIndex + j).getValue = getOutputAngle;
            this._physicsRig.outputs.at(outputIndex + j).getScale = getOutputScaleAngle;
          }
          this._physicsRig.outputs.at(outputIndex + j).reflect = json.getOutputReflect(i, j);
        }
        this._currentRigOutputs.pushBack(currentRigOutput);
        this._previousRigOutputs.pushBack(previousRigOutput);
        outputIndex += this._physicsRig.settings.at(i).outputCount;
        this._physicsRig.settings.at(i).particleCount = json.getParticleCount(i);
        this._physicsRig.settings.at(i).baseParticleIndex = particleIndex;
        for (let j = 0; j < this._physicsRig.settings.at(i).particleCount; ++j) {
          this._physicsRig.particles.at(particleIndex + j).mobility = json.getParticleMobility(i, j);
          this._physicsRig.particles.at(particleIndex + j).delay = json.getParticleDelay(i, j);
          this._physicsRig.particles.at(particleIndex + j).acceleration = json.getParticleAcceleration(i, j);
          this._physicsRig.particles.at(particleIndex + j).radius = json.getParticleRadius(i, j);
          this._physicsRig.particles.at(particleIndex + j).position = json.getParticlePosition(i, j);
        }
        particleIndex += this._physicsRig.settings.at(i).particleCount;
      }
      this.initialize();
      json.release();
      json = void 0;
      json = null;
    }
    /**
     * 現在のパラメータ値で物理演算が安定化する状態を演算する。
     * @param model 物理演算の結果を適用するモデル
     */
    stabilization(model) {
      var _a, _b, _c, _d;
      let totalAngle;
      let weight;
      let radAngle;
      let outputValue;
      const totalTranslation = new CubismVector2();
      let currentSetting;
      let currentInputs;
      let currentOutputs;
      let currentParticles;
      const parameterValues = model.getModel().parameters.values;
      const parameterMaximumValues = model.getModel().parameters.maximumValues;
      const parameterMinimumValues = model.getModel().parameters.minimumValues;
      const parameterDefaultValues = model.getModel().parameters.defaultValues;
      if (((_b = (_a = this._parameterCaches) == null ? void 0 : _a.length) != null ? _b : 0) < model.getParameterCount()) {
        this._parameterCaches = new Float32Array(model.getParameterCount());
      }
      if (((_d = (_c = this._parameterInputCaches) == null ? void 0 : _c.length) != null ? _d : 0) < model.getParameterCount()) {
        this._parameterInputCaches = new Float32Array(model.getParameterCount());
      }
      for (let j = 0; j < model.getParameterCount(); ++j) {
        this._parameterCaches[j] = parameterValues[j];
        this._parameterInputCaches[j] = parameterValues[j];
      }
      for (let settingIndex = 0; settingIndex < this._physicsRig.subRigCount; ++settingIndex) {
        totalAngle = { angle: 0 };
        totalTranslation.x = 0;
        totalTranslation.y = 0;
        currentSetting = this._physicsRig.settings.at(settingIndex);
        currentInputs = this._physicsRig.inputs.get(
          currentSetting.baseInputIndex
        );
        currentOutputs = this._physicsRig.outputs.get(
          currentSetting.baseOutputIndex
        );
        currentParticles = this._physicsRig.particles.get(
          currentSetting.baseParticleIndex
        );
        for (let i = 0; i < currentSetting.inputCount; ++i) {
          weight = currentInputs[i].weight / MaximumWeight;
          if (currentInputs[i].sourceParameterIndex == -1) {
            currentInputs[i].sourceParameterIndex = model.getParameterIndex(
              currentInputs[i].source.id
            );
          }
          currentInputs[i].getNormalizedParameterValue(
            totalTranslation,
            totalAngle,
            parameterValues[currentInputs[i].sourceParameterIndex],
            parameterMinimumValues[currentInputs[i].sourceParameterIndex],
            parameterMaximumValues[currentInputs[i].sourceParameterIndex],
            parameterDefaultValues[currentInputs[i].sourceParameterIndex],
            currentSetting.normalizationPosition,
            currentSetting.normalizationAngle,
            currentInputs[i].reflect,
            weight
          );
          this._parameterCaches[currentInputs[i].sourceParameterIndex] = parameterValues[currentInputs[i].sourceParameterIndex];
        }
        radAngle = CubismMath.degreesToRadian(-totalAngle.angle);
        totalTranslation.x = totalTranslation.x * CubismMath.cos(radAngle) - totalTranslation.y * CubismMath.sin(radAngle);
        totalTranslation.y = totalTranslation.x * CubismMath.sin(radAngle) + totalTranslation.y * CubismMath.cos(radAngle);
        updateParticlesForStabilization(
          currentParticles,
          currentSetting.particleCount,
          totalTranslation,
          totalAngle.angle,
          this._options.wind,
          MovementThreshold * currentSetting.normalizationPosition.maximum
        );
        for (let i = 0; i < currentSetting.outputCount; ++i) {
          const particleIndex = currentOutputs[i].vertexIndex;
          if (currentOutputs[i].destinationParameterIndex == -1) {
            currentOutputs[i].destinationParameterIndex = model.getParameterIndex(
              currentOutputs[i].destination.id
            );
          }
          if (particleIndex < 1 || particleIndex >= currentSetting.particleCount) {
            continue;
          }
          let translation = new CubismVector2();
          translation = currentParticles[particleIndex].position.substract(
            currentParticles[particleIndex - 1].position
          );
          outputValue = currentOutputs[i].getValue(
            translation,
            currentParticles,
            particleIndex,
            currentOutputs[i].reflect,
            this._options.gravity
          );
          this._currentRigOutputs.at(settingIndex).outputs.set(i, outputValue);
          this._previousRigOutputs.at(settingIndex).outputs.set(i, outputValue);
          const destinationParameterIndex = currentOutputs[i].destinationParameterIndex;
          const outParameterCaches = !Float32Array.prototype.slice && "subarray" in Float32Array.prototype ? JSON.parse(
            JSON.stringify(
              parameterValues.subarray(destinationParameterIndex)
            )
          ) : parameterValues.slice(destinationParameterIndex);
          updateOutputParameterValue(
            outParameterCaches,
            parameterMinimumValues[destinationParameterIndex],
            parameterMaximumValues[destinationParameterIndex],
            outputValue,
            currentOutputs[i]
          );
          for (let offset = destinationParameterIndex, outParamIndex = 0; offset < this._parameterCaches.length; offset++, outParamIndex++) {
            parameterValues[offset] = this._parameterCaches[offset] = outParameterCaches[outParamIndex];
          }
        }
      }
    }
    /**
     * 物理演算の評価
     *
     * Pendulum interpolation weights
     *
     * 振り子の計算結果は保存され、パラメータへの出力は保存された前回の結果で補間されます。
     * The result of the pendulum calculation is saved and
     * the output to the parameters is interpolated with the saved previous result of the pendulum calculation.
     *
     * 図で示すと[1]と[2]で補間されます。
     * The figure shows the interpolation between [1] and [2].
     *
     * 補間の重みは最新の振り子計算タイミングと次回のタイミングの間で見た現在時間で決定する。
     * The weight of the interpolation are determined by the current time seen between
     * the latest pendulum calculation timing and the next timing.
     *
     * 図で示すと[2]と[4]の間でみた(3)の位置の重みになる。
     * Figure shows the weight of position (3) as seen between [2] and [4].
     *
     * 解釈として振り子計算のタイミングと重み計算のタイミングがズレる。
     * As an interpretation, the pendulum calculation and weights are misaligned.
     *
     * physics3.jsonにFPS情報が存在しない場合は常に前の振り子状態で設定される。
     * If there is no FPS information in physics3.json, it is always set in the previous pendulum state.
     *
     * この仕様は補間範囲を逸脱したことが原因の震えたような見た目を回避を目的にしている。
     * The purpose of this specification is to avoid the quivering appearance caused by deviations from the interpolation range.
     *
     * ------------ time -------------->
     *
     *                 |+++++|------| <- weight
     * ==[1]====#=====[2]---(3)----(4)
     *          ^ output contents
     *
     * 1:_previousRigOutputs
     * 2:_currentRigOutputs
     * 3:_currentRemainTime (now rendering)
     * 4:next particles timing
     * @param model 物理演算の結果を適用するモデル
     * @param deltaTimeSeconds デルタ時間[秒]
     */
    evaluate(model, deltaTimeSeconds) {
      var _a, _b, _c, _d;
      let totalAngle;
      let weight;
      let radAngle;
      let outputValue;
      const totalTranslation = new CubismVector2();
      let currentSetting;
      let currentInputs;
      let currentOutputs;
      let currentParticles;
      if (0 >= deltaTimeSeconds) {
        return;
      }
      const parameterValues = model.getModel().parameters.values;
      const parameterMaximumValues = model.getModel().parameters.maximumValues;
      const parameterMinimumValues = model.getModel().parameters.minimumValues;
      const parameterDefaultValues = model.getModel().parameters.defaultValues;
      let physicsDeltaTime;
      this._currentRemainTime += deltaTimeSeconds;
      if (this._currentRemainTime > MaxDeltaTime) {
        this._currentRemainTime = 0;
      }
      if (((_b = (_a = this._parameterCaches) == null ? void 0 : _a.length) != null ? _b : 0) < model.getParameterCount()) {
        this._parameterCaches = new Float32Array(model.getParameterCount());
      }
      if (((_d = (_c = this._parameterInputCaches) == null ? void 0 : _c.length) != null ? _d : 0) < model.getParameterCount()) {
        this._parameterInputCaches = new Float32Array(model.getParameterCount());
        for (let j = 0; j < model.getParameterCount(); ++j) {
          this._parameterInputCaches[j] = parameterValues[j];
        }
      }
      if (this._physicsRig.fps > 0) {
        physicsDeltaTime = 1 / this._physicsRig.fps;
      } else {
        physicsDeltaTime = deltaTimeSeconds;
      }
      while (this._currentRemainTime >= physicsDeltaTime) {
        for (let settingIndex = 0; settingIndex < this._physicsRig.subRigCount; ++settingIndex) {
          currentSetting = this._physicsRig.settings.at(settingIndex);
          currentOutputs = this._physicsRig.outputs.get(
            currentSetting.baseOutputIndex
          );
          for (let i = 0; i < currentSetting.outputCount; ++i) {
            this._previousRigOutputs.at(settingIndex).outputs.set(
              i,
              this._currentRigOutputs.at(settingIndex).outputs.at(i)
            );
          }
        }
        const inputWeight = physicsDeltaTime / this._currentRemainTime;
        for (let j = 0; j < model.getParameterCount(); ++j) {
          this._parameterCaches[j] = this._parameterInputCaches[j] * (1 - inputWeight) + parameterValues[j] * inputWeight;
          this._parameterInputCaches[j] = this._parameterCaches[j];
        }
        for (let settingIndex = 0; settingIndex < this._physicsRig.subRigCount; ++settingIndex) {
          totalAngle = { angle: 0 };
          totalTranslation.x = 0;
          totalTranslation.y = 0;
          currentSetting = this._physicsRig.settings.at(settingIndex);
          currentInputs = this._physicsRig.inputs.get(
            currentSetting.baseInputIndex
          );
          currentOutputs = this._physicsRig.outputs.get(
            currentSetting.baseOutputIndex
          );
          currentParticles = this._physicsRig.particles.get(
            currentSetting.baseParticleIndex
          );
          for (let i = 0; i < currentSetting.inputCount; ++i) {
            weight = currentInputs[i].weight / MaximumWeight;
            if (currentInputs[i].sourceParameterIndex == -1) {
              currentInputs[i].sourceParameterIndex = model.getParameterIndex(
                currentInputs[i].source.id
              );
            }
            currentInputs[i].getNormalizedParameterValue(
              totalTranslation,
              totalAngle,
              this._parameterCaches[currentInputs[i].sourceParameterIndex],
              parameterMinimumValues[currentInputs[i].sourceParameterIndex],
              parameterMaximumValues[currentInputs[i].sourceParameterIndex],
              parameterDefaultValues[currentInputs[i].sourceParameterIndex],
              currentSetting.normalizationPosition,
              currentSetting.normalizationAngle,
              currentInputs[i].reflect,
              weight
            );
          }
          radAngle = CubismMath.degreesToRadian(-totalAngle.angle);
          totalTranslation.x = totalTranslation.x * CubismMath.cos(radAngle) - totalTranslation.y * CubismMath.sin(radAngle);
          totalTranslation.y = totalTranslation.x * CubismMath.sin(radAngle) + totalTranslation.y * CubismMath.cos(radAngle);
          updateParticles(
            currentParticles,
            currentSetting.particleCount,
            totalTranslation,
            totalAngle.angle,
            this._options.wind,
            MovementThreshold * currentSetting.normalizationPosition.maximum,
            physicsDeltaTime,
            AirResistance
          );
          for (let i = 0; i < currentSetting.outputCount; ++i) {
            const particleIndex = currentOutputs[i].vertexIndex;
            if (currentOutputs[i].destinationParameterIndex == -1) {
              currentOutputs[i].destinationParameterIndex = model.getParameterIndex(currentOutputs[i].destination.id);
            }
            if (particleIndex < 1 || particleIndex >= currentSetting.particleCount) {
              continue;
            }
            const translation = new CubismVector2();
            translation.x = currentParticles[particleIndex].position.x - currentParticles[particleIndex - 1].position.x;
            translation.y = currentParticles[particleIndex].position.y - currentParticles[particleIndex - 1].position.y;
            outputValue = currentOutputs[i].getValue(
              translation,
              currentParticles,
              particleIndex,
              currentOutputs[i].reflect,
              this._options.gravity
            );
            this._currentRigOutputs.at(settingIndex).outputs.set(i, outputValue);
            const destinationParameterIndex = currentOutputs[i].destinationParameterIndex;
            const outParameterCaches = !Float32Array.prototype.slice && "subarray" in Float32Array.prototype ? JSON.parse(
              JSON.stringify(
                this._parameterCaches.subarray(destinationParameterIndex)
              )
            ) : this._parameterCaches.slice(destinationParameterIndex);
            updateOutputParameterValue(
              outParameterCaches,
              parameterMinimumValues[destinationParameterIndex],
              parameterMaximumValues[destinationParameterIndex],
              outputValue,
              currentOutputs[i]
            );
            for (let offset = destinationParameterIndex, outParamIndex = 0; offset < this._parameterCaches.length; offset++, outParamIndex++) {
              this._parameterCaches[offset] = outParameterCaches[outParamIndex];
            }
          }
        }
        this._currentRemainTime -= physicsDeltaTime;
      }
      const alpha = this._currentRemainTime / physicsDeltaTime;
      this.interpolate(model, alpha);
    }
    /**
     * 物理演算結果の適用
     * 振り子演算の最新の結果と一つ前の結果から指定した重みで適用する。
     * @param model 物理演算の結果を適用するモデル
     * @param weight 最新結果の重み
     */
    interpolate(model, weight) {
      let currentOutputs;
      let currentSetting;
      const parameterValues = model.getModel().parameters.values;
      const parameterMaximumValues = model.getModel().parameters.maximumValues;
      const parameterMinimumValues = model.getModel().parameters.minimumValues;
      for (let settingIndex = 0; settingIndex < this._physicsRig.subRigCount; ++settingIndex) {
        currentSetting = this._physicsRig.settings.at(settingIndex);
        currentOutputs = this._physicsRig.outputs.get(
          currentSetting.baseOutputIndex
        );
        for (let i = 0; i < currentSetting.outputCount; ++i) {
          if (currentOutputs[i].destinationParameterIndex == -1) {
            continue;
          }
          const destinationParameterIndex = currentOutputs[i].destinationParameterIndex;
          const outParameterValues = !Float32Array.prototype.slice && "subarray" in Float32Array.prototype ? JSON.parse(
            JSON.stringify(
              parameterValues.subarray(destinationParameterIndex)
            )
          ) : parameterValues.slice(destinationParameterIndex);
          updateOutputParameterValue(
            outParameterValues,
            parameterMinimumValues[destinationParameterIndex],
            parameterMaximumValues[destinationParameterIndex],
            this._previousRigOutputs.at(settingIndex).outputs.at(i) * (1 - weight) + this._currentRigOutputs.at(settingIndex).outputs.at(i) * weight,
            currentOutputs[i]
          );
          for (let offset = destinationParameterIndex, outParamIndex = 0; offset < parameterValues.length; offset++, outParamIndex++) {
            parameterValues[offset] = outParameterValues[outParamIndex];
          }
        }
      }
    }
    /**
     * オプションの設定
     * @param options オプション
     */
    setOptions(options) {
      this._options = options;
    }
    /**
     * オプションの取得
     * @return オプション
     */
    getOption() {
      return this._options;
    }
    /**
     * デストラクタ相当の処理
     */
    release() {
      this._physicsRig = void 0;
      this._physicsRig = null;
    }
    /**
     * 初期化する
     */
    initialize() {
      let strand;
      let currentSetting;
      let radius;
      for (let settingIndex = 0; settingIndex < this._physicsRig.subRigCount; ++settingIndex) {
        currentSetting = this._physicsRig.settings.at(settingIndex);
        strand = this._physicsRig.particles.get(currentSetting.baseParticleIndex);
        strand[0].initialPosition = new CubismVector2(0, 0);
        strand[0].lastPosition = new CubismVector2(
          strand[0].initialPosition.x,
          strand[0].initialPosition.y
        );
        strand[0].lastGravity = new CubismVector2(0, -1);
        strand[0].lastGravity.y *= -1;
        strand[0].velocity = new CubismVector2(0, 0);
        strand[0].force = new CubismVector2(0, 0);
        for (let i = 1; i < currentSetting.particleCount; ++i) {
          radius = new CubismVector2(0, 0);
          radius.y = strand[i].radius;
          strand[i].initialPosition = new CubismVector2(
            strand[i - 1].initialPosition.x + radius.x,
            strand[i - 1].initialPosition.y + radius.y
          );
          strand[i].position = new CubismVector2(
            strand[i].initialPosition.x,
            strand[i].initialPosition.y
          );
          strand[i].lastPosition = new CubismVector2(
            strand[i].initialPosition.x,
            strand[i].initialPosition.y
          );
          strand[i].lastGravity = new CubismVector2(0, -1);
          strand[i].lastGravity.y *= -1;
          strand[i].velocity = new CubismVector2(0, 0);
          strand[i].force = new CubismVector2(0, 0);
        }
      }
    }
    ///< UpdateParticlesが動くときの入力をキャッシュ
  };
  var Options = class {
    constructor() {
      __publicField(this, "gravity");
      // 重力方向
      __publicField(this, "wind");
      this.gravity = new CubismVector2(0, 0);
      this.wind = new CubismVector2(0, 0);
    }
    // 風の方向
  };
  var PhysicsOutput = class {
    constructor() {
      __publicField(this, "outputs");
      this.outputs = new csmVector(0);
    }
    // 物理演算出力結果
  };
  function sign(value) {
    let ret = 0;
    if (value > 0) {
      ret = 1;
    } else if (value < 0) {
      ret = -1;
    }
    return ret;
  }
  function getInputTranslationXFromNormalizedParameterValue(targetTranslation, targetAngle, value, parameterMinimumValue, parameterMaximumValue, parameterDefaultValue, normalizationPosition, normalizationAngle, isInverted, weight) {
    targetTranslation.x += normalizeParameterValue(
      value,
      parameterMinimumValue,
      parameterMaximumValue,
      parameterDefaultValue,
      normalizationPosition.minimum,
      normalizationPosition.maximum,
      normalizationPosition.defalut,
      isInverted
    ) * weight;
  }
  function getInputTranslationYFromNormalizedParamterValue(targetTranslation, targetAngle, value, parameterMinimumValue, parameterMaximumValue, parameterDefaultValue, normalizationPosition, normalizationAngle, isInverted, weight) {
    targetTranslation.y += normalizeParameterValue(
      value,
      parameterMinimumValue,
      parameterMaximumValue,
      parameterDefaultValue,
      normalizationPosition.minimum,
      normalizationPosition.maximum,
      normalizationPosition.defalut,
      isInverted
    ) * weight;
  }
  function getInputAngleFromNormalizedParameterValue(targetTranslation, targetAngle, value, parameterMinimumValue, parameterMaximumValue, parameterDefaultValue, normalizaitionPosition, normalizationAngle, isInverted, weight) {
    targetAngle.angle += normalizeParameterValue(
      value,
      parameterMinimumValue,
      parameterMaximumValue,
      parameterDefaultValue,
      normalizationAngle.minimum,
      normalizationAngle.maximum,
      normalizationAngle.defalut,
      isInverted
    ) * weight;
  }
  function getOutputTranslationX(translation, particles, particleIndex, isInverted, parentGravity) {
    let outputValue = translation.x;
    if (isInverted) {
      outputValue *= -1;
    }
    return outputValue;
  }
  function getOutputTranslationY(translation, particles, particleIndex, isInverted, parentGravity) {
    let outputValue = translation.y;
    if (isInverted) {
      outputValue *= -1;
    }
    return outputValue;
  }
  function getOutputAngle(translation, particles, particleIndex, isInverted, parentGravity) {
    let outputValue;
    if (particleIndex >= 2) {
      parentGravity = particles[particleIndex - 1].position.substract(
        particles[particleIndex - 2].position
      );
    } else {
      parentGravity = parentGravity.multiplyByScaler(-1);
    }
    outputValue = CubismMath.directionToRadian(parentGravity, translation);
    if (isInverted) {
      outputValue *= -1;
    }
    return outputValue;
  }
  function getRangeValue(min, max) {
    const maxValue = CubismMath.max(min, max);
    const minValue = CubismMath.min(min, max);
    return CubismMath.abs(maxValue - minValue);
  }
  function getDefaultValue(min, max) {
    const minValue = CubismMath.min(min, max);
    return minValue + getRangeValue(min, max) / 2;
  }
  function getOutputScaleTranslationX(translationScale, angleScale) {
    return JSON.parse(JSON.stringify(translationScale.x));
  }
  function getOutputScaleTranslationY(translationScale, angleScale) {
    return JSON.parse(JSON.stringify(translationScale.y));
  }
  function getOutputScaleAngle(translationScale, angleScale) {
    return JSON.parse(JSON.stringify(angleScale));
  }
  function updateParticles(strand, strandCount, totalTranslation, totalAngle, windDirection, thresholdValue, deltaTimeSeconds, airResistance) {
    let delay;
    let radian;
    let direction = new CubismVector2(0, 0);
    let velocity = new CubismVector2(0, 0);
    let force = new CubismVector2(0, 0);
    let newDirection = new CubismVector2(0, 0);
    strand[0].position = new CubismVector2(
      totalTranslation.x,
      totalTranslation.y
    );
    const totalRadian = CubismMath.degreesToRadian(totalAngle);
    const currentGravity = CubismMath.radianToDirection(totalRadian);
    currentGravity.normalize();
    for (let i = 1; i < strandCount; ++i) {
      strand[i].force = currentGravity.multiplyByScaler(strand[i].acceleration).add(windDirection);
      strand[i].lastPosition = new CubismVector2(
        strand[i].position.x,
        strand[i].position.y
      );
      delay = strand[i].delay * deltaTimeSeconds * 30;
      direction = strand[i].position.substract(strand[i - 1].position);
      radian = CubismMath.directionToRadian(strand[i].lastGravity, currentGravity) / airResistance;
      direction.x = CubismMath.cos(radian) * direction.x - direction.y * CubismMath.sin(radian);
      direction.y = CubismMath.sin(radian) * direction.x + direction.y * CubismMath.cos(radian);
      strand[i].position = strand[i - 1].position.add(direction);
      velocity = strand[i].velocity.multiplyByScaler(delay);
      force = strand[i].force.multiplyByScaler(delay).multiplyByScaler(delay);
      strand[i].position = strand[i].position.add(velocity).add(force);
      newDirection = strand[i].position.substract(strand[i - 1].position);
      newDirection.normalize();
      strand[i].position = strand[i - 1].position.add(
        newDirection.multiplyByScaler(strand[i].radius)
      );
      if (CubismMath.abs(strand[i].position.x) < thresholdValue) {
        strand[i].position.x = 0;
      }
      if (delay != 0) {
        strand[i].velocity = strand[i].position.substract(strand[i].lastPosition);
        strand[i].velocity = strand[i].velocity.divisionByScalar(delay);
        strand[i].velocity = strand[i].velocity.multiplyByScaler(
          strand[i].mobility
        );
      }
      strand[i].force = new CubismVector2(0, 0);
      strand[i].lastGravity = new CubismVector2(
        currentGravity.x,
        currentGravity.y
      );
    }
  }
  function updateParticlesForStabilization(strand, strandCount, totalTranslation, totalAngle, windDirection, thresholdValue) {
    let force = new CubismVector2(0, 0);
    strand[0].position = new CubismVector2(
      totalTranslation.x,
      totalTranslation.y
    );
    const totalRadian = CubismMath.degreesToRadian(totalAngle);
    const currentGravity = CubismMath.radianToDirection(totalRadian);
    currentGravity.normalize();
    for (let i = 1; i < strandCount; ++i) {
      strand[i].force = currentGravity.multiplyByScaler(strand[i].acceleration).add(windDirection);
      strand[i].lastPosition = new CubismVector2(
        strand[i].position.x,
        strand[i].position.y
      );
      strand[i].velocity = new CubismVector2(0, 0);
      force = strand[i].force;
      force.normalize();
      force = force.multiplyByScaler(strand[i].radius);
      strand[i].position = strand[i - 1].position.add(force);
      if (CubismMath.abs(strand[i].position.x) < thresholdValue) {
        strand[i].position.x = 0;
      }
      strand[i].force = new CubismVector2(0, 0);
      strand[i].lastGravity = new CubismVector2(
        currentGravity.x,
        currentGravity.y
      );
    }
  }
  function updateOutputParameterValue(parameterValue, parameterValueMinimum, parameterValueMaximum, translation, output) {
    let value;
    const outputScale = output.getScale(
      output.translationScale,
      output.angleScale
    );
    value = translation * outputScale;
    if (value < parameterValueMinimum) {
      if (value < output.valueBelowMinimum) {
        output.valueBelowMinimum = value;
      }
      value = parameterValueMinimum;
    } else if (value > parameterValueMaximum) {
      if (value > output.valueExceededMaximum) {
        output.valueExceededMaximum = value;
      }
      value = parameterValueMaximum;
    }
    const weight = output.weight / MaximumWeight;
    if (weight >= 1) {
      parameterValue[0] = value;
    } else {
      value = parameterValue[0] * (1 - weight) + value * weight;
      parameterValue[0] = value;
    }
  }
  function normalizeParameterValue(value, parameterMinimum, parameterMaximum, parameterDefault, normalizedMinimum, normalizedMaximum, normalizedDefault, isInverted) {
    let result = 0;
    const maxValue = CubismMath.max(parameterMaximum, parameterMinimum);
    if (maxValue < value) {
      value = maxValue;
    }
    const minValue = CubismMath.min(parameterMaximum, parameterMinimum);
    if (minValue > value) {
      value = minValue;
    }
    const minNormValue = CubismMath.min(
      normalizedMinimum,
      normalizedMaximum
    );
    const maxNormValue = CubismMath.max(
      normalizedMinimum,
      normalizedMaximum
    );
    const middleNormValue = normalizedDefault;
    const middleValue = getDefaultValue(minValue, maxValue);
    const paramValue = value - middleValue;
    switch (sign(paramValue)) {
      case 1: {
        const nLength = maxNormValue - middleNormValue;
        const pLength = maxValue - middleValue;
        if (pLength != 0) {
          result = paramValue * (nLength / pLength);
          result += middleNormValue;
        }
        break;
      }
      case -1: {
        const nLength = minNormValue - middleNormValue;
        const pLength = minValue - middleValue;
        if (pLength != 0) {
          result = paramValue * (nLength / pLength);
          result += middleNormValue;
        }
        break;
      }
      case 0: {
        result = middleNormValue;
        break;
      }
      default: {
        break;
      }
    }
    return isInverted ? result : result * -1;
  }
  var Live2DCubismFramework33;
  ((Live2DCubismFramework42) => {
    Live2DCubismFramework42.CubismPhysics = CubismPhysics;
    Live2DCubismFramework42.Options = Options;
  })(Live2DCubismFramework33 || (Live2DCubismFramework33 = {}));

  // .trellis/workspace/lapp-runtime-src/src/renderer/WebSDK/Framework/src/rendering/cubismclippingmanager.ts
  var ColorChannelCount = 4;
  var ClippingMaskMaxCountOnDefault = 36;
  var ClippingMaskMaxCountOnMultiRenderTexture = 32;
  var CubismClippingManager = class {
    /**
     * コンストラクタ
     */
    constructor(clippingContextFactory) {
      __publicField(this, "_clearedFrameBufferFlags");
      //マスクのクリアフラグの配列
      __publicField(this, "_channelColors");
      __publicField(this, "_clippingContextListForMask");
      // マスク用クリッピングコンテキストのリスト
      __publicField(this, "_clippingContextListForDraw");
      // 描画用クリッピングコンテキストのリスト
      __publicField(this, "_clippingMaskBufferSize");
      // クリッピングマスクのバッファサイズ（初期値:256）
      __publicField(this, "_renderTextureCount");
      // 生成するレンダーテクスチャの枚数
      __publicField(this, "_tmpMatrix");
      // マスク計算用の行列
      __publicField(this, "_tmpMatrixForMask");
      // マスク計算用の行列
      __publicField(this, "_tmpMatrixForDraw");
      // マスク計算用の行列
      __publicField(this, "_tmpBoundsOnModel");
      // マスク配置計算用の矩形
      __publicField(this, "_clippingContexttConstructor");
      this._renderTextureCount = 0;
      this._clippingMaskBufferSize = 256;
      this._clippingContextListForMask = new csmVector();
      this._clippingContextListForDraw = new csmVector();
      this._channelColors = new csmVector();
      this._tmpBoundsOnModel = new csmRect();
      this._tmpMatrix = new CubismMatrix44();
      this._tmpMatrixForMask = new CubismMatrix44();
      this._tmpMatrixForDraw = new CubismMatrix44();
      this._clippingContexttConstructor = clippingContextFactory;
      let tmp = new CubismTextureColor();
      tmp.r = 1;
      tmp.g = 0;
      tmp.b = 0;
      tmp.a = 0;
      this._channelColors.pushBack(tmp);
      tmp = new CubismTextureColor();
      tmp.r = 0;
      tmp.g = 1;
      tmp.b = 0;
      tmp.a = 0;
      this._channelColors.pushBack(tmp);
      tmp = new CubismTextureColor();
      tmp.r = 0;
      tmp.g = 0;
      tmp.b = 1;
      tmp.a = 0;
      this._channelColors.pushBack(tmp);
      tmp = new CubismTextureColor();
      tmp.r = 0;
      tmp.g = 0;
      tmp.b = 0;
      tmp.a = 1;
      this._channelColors.pushBack(tmp);
    }
    /**
     * デストラクタ相当の処理
     */
    release() {
      for (let i = 0; i < this._clippingContextListForMask.getSize(); i++) {
        if (this._clippingContextListForMask.at(i)) {
          this._clippingContextListForMask.at(i).release();
          this._clippingContextListForMask.set(i, void 0);
        }
        this._clippingContextListForMask.set(i, null);
      }
      this._clippingContextListForMask = null;
      for (let i = 0; i < this._clippingContextListForDraw.getSize(); i++) {
        this._clippingContextListForDraw.set(i, null);
      }
      this._clippingContextListForDraw = null;
      for (let i = 0; i < this._channelColors.getSize(); i++) {
        this._channelColors.set(i, null);
      }
      this._channelColors = null;
      if (this._clearedFrameBufferFlags != null) {
        this._clearedFrameBufferFlags.clear();
      }
      this._clearedFrameBufferFlags = null;
    }
    /**
     * マネージャの初期化処理
     * クリッピングマスクを使う描画オブジェクトの登録を行う
     * @param model モデルのインスタンス
     * @param renderTextureCount バッファの生成数
     */
    initialize(model, renderTextureCount) {
      if (renderTextureCount % 1 != 0) {
        CubismLogWarning(
          "The number of render textures must be specified as an integer. The decimal point is rounded down and corrected to an integer."
        );
        renderTextureCount = ~~renderTextureCount;
      }
      if (renderTextureCount < 1) {
        CubismLogWarning(
          "The number of render textures must be an integer greater than or equal to 1. Set the number of render textures to 1."
        );
      }
      this._renderTextureCount = renderTextureCount < 1 ? 1 : renderTextureCount;
      this._clearedFrameBufferFlags = new csmVector(
        this._renderTextureCount
      );
      for (let i = 0; i < model.getDrawableCount(); i++) {
        if (model.getDrawableMaskCounts()[i] <= 0) {
          this._clippingContextListForDraw.pushBack(null);
          continue;
        }
        let clippingContext = this.findSameClip(
          model.getDrawableMasks()[i],
          model.getDrawableMaskCounts()[i]
        );
        if (clippingContext == null) {
          clippingContext = new this._clippingContexttConstructor(
            this,
            model.getDrawableMasks()[i],
            model.getDrawableMaskCounts()[i]
          );
          this._clippingContextListForMask.pushBack(clippingContext);
        }
        clippingContext.addClippedDrawable(i);
        this._clippingContextListForDraw.pushBack(clippingContext);
      }
    }
    /**
     * 既にマスクを作っているかを確認
     * 作っている様であれば該当するクリッピングマスクのインスタンスを返す
     * 作っていなければNULLを返す
     * @param drawableMasks 描画オブジェクトをマスクする描画オブジェクトのリスト
     * @param drawableMaskCounts 描画オブジェクトをマスクする描画オブジェクトの数
     * @return 該当するクリッピングマスクが存在すればインスタンスを返し、なければNULLを返す
     */
    findSameClip(drawableMasks, drawableMaskCounts) {
      for (let i = 0; i < this._clippingContextListForMask.getSize(); i++) {
        const clippingContext = this._clippingContextListForMask.at(i);
        const count = clippingContext._clippingIdCount;
        if (count != drawableMaskCounts) {
          continue;
        }
        let sameCount = 0;
        for (let j = 0; j < count; j++) {
          const clipId = clippingContext._clippingIdList[j];
          for (let k = 0; k < count; k++) {
            if (drawableMasks[k] == clipId) {
              sameCount++;
              break;
            }
          }
        }
        if (sameCount == count) {
          return clippingContext;
        }
      }
      return null;
    }
    /**
     * 高精細マスク処理用の行列を計算する
     * @param model モデルのインスタンス
     * @param isRightHanded 処理が右手系であるか
     */
    setupMatrixForHighPrecision(model, isRightHanded) {
      let usingClipCount = 0;
      for (let clipIndex = 0; clipIndex < this._clippingContextListForMask.getSize(); clipIndex++) {
        const cc = this._clippingContextListForMask.at(clipIndex);
        this.calcClippedDrawTotalBounds(model, cc);
        if (cc._isUsing) {
          usingClipCount++;
        }
      }
      if (usingClipCount > 0) {
        this.setupLayoutBounds(0);
        if (this._clearedFrameBufferFlags.getSize() != this._renderTextureCount) {
          this._clearedFrameBufferFlags.clear();
          for (let i = 0; i < this._renderTextureCount; i++) {
            this._clearedFrameBufferFlags.pushBack(false);
          }
        } else {
          for (let i = 0; i < this._renderTextureCount; i++) {
            this._clearedFrameBufferFlags.set(i, false);
          }
        }
        for (let clipIndex = 0; clipIndex < this._clippingContextListForMask.getSize(); clipIndex++) {
          const clipContext = this._clippingContextListForMask.at(clipIndex);
          const allClippedDrawRect = clipContext._allClippedDrawRect;
          const layoutBoundsOnTex01 = clipContext._layoutBounds;
          const margin = 0.05;
          let scaleX = 0;
          let scaleY = 0;
          const ppu = model.getPixelsPerUnit();
          const maskPixelSize = clipContext.getClippingManager().getClippingMaskBufferSize();
          const physicalMaskWidth = layoutBoundsOnTex01.width * maskPixelSize;
          const physicalMaskHeight = layoutBoundsOnTex01.height * maskPixelSize;
          this._tmpBoundsOnModel.setRect(allClippedDrawRect);
          if (this._tmpBoundsOnModel.width * ppu > physicalMaskWidth) {
            this._tmpBoundsOnModel.expand(allClippedDrawRect.width * margin, 0);
            scaleX = layoutBoundsOnTex01.width / this._tmpBoundsOnModel.width;
          } else {
            scaleX = ppu / physicalMaskWidth;
          }
          if (this._tmpBoundsOnModel.height * ppu > physicalMaskHeight) {
            this._tmpBoundsOnModel.expand(
              0,
              allClippedDrawRect.height * margin
            );
            scaleY = layoutBoundsOnTex01.height / this._tmpBoundsOnModel.height;
          } else {
            scaleY = ppu / physicalMaskHeight;
          }
          this.createMatrixForMask(
            isRightHanded,
            layoutBoundsOnTex01,
            scaleX,
            scaleY
          );
          clipContext._matrixForMask.setMatrix(this._tmpMatrixForMask.getArray());
          clipContext._matrixForDraw.setMatrix(this._tmpMatrixForDraw.getArray());
        }
      }
    }
    /**
     * マスク作成・描画用の行列を作成する。
     * @param isRightHanded 座標を右手系として扱うかを指定
     * @param layoutBoundsOnTex01 マスクを収める領域
     * @param scaleX 描画オブジェクトの伸縮率
     * @param scaleY 描画オブジェクトの伸縮率
     */
    createMatrixForMask(isRightHanded, layoutBoundsOnTex01, scaleX, scaleY) {
      this._tmpMatrix.loadIdentity();
      {
        this._tmpMatrix.translateRelative(-1, -1);
        this._tmpMatrix.scaleRelative(2, 2);
      }
      {
        this._tmpMatrix.translateRelative(
          layoutBoundsOnTex01.x,
          layoutBoundsOnTex01.y
        );
        this._tmpMatrix.scaleRelative(scaleX, scaleY);
        this._tmpMatrix.translateRelative(
          -this._tmpBoundsOnModel.x,
          -this._tmpBoundsOnModel.y
        );
      }
      this._tmpMatrixForMask.setMatrix(this._tmpMatrix.getArray());
      this._tmpMatrix.loadIdentity();
      {
        this._tmpMatrix.translateRelative(
          layoutBoundsOnTex01.x,
          layoutBoundsOnTex01.y * (isRightHanded ? -1 : 1)
        );
        this._tmpMatrix.scaleRelative(
          scaleX,
          scaleY * (isRightHanded ? -1 : 1)
        );
        this._tmpMatrix.translateRelative(
          -this._tmpBoundsOnModel.x,
          -this._tmpBoundsOnModel.y
        );
      }
      this._tmpMatrixForDraw.setMatrix(this._tmpMatrix.getArray());
    }
    /**
     * クリッピングコンテキストを配置するレイアウト
     * 指定された数のレンダーテクスチャを極力いっぱいに使ってマスクをレイアウトする
     * マスクグループの数が4以下ならRGBA各チャンネルに一つずつマスクを配置し、5以上6以下ならRGBAを2,2,1,1と配置する。
     *
     * @param usingClipCount 配置するクリッピングコンテキストの数
     */
    setupLayoutBounds(usingClipCount) {
      const useClippingMaskMaxCount = this._renderTextureCount <= 1 ? ClippingMaskMaxCountOnDefault : ClippingMaskMaxCountOnMultiRenderTexture * this._renderTextureCount;
      if (usingClipCount <= 0 || usingClipCount > useClippingMaskMaxCount) {
        if (usingClipCount > useClippingMaskMaxCount) {
          CubismLogError(
            "not supported mask count : {0}\n[Details] render texture count : {1}, mask count : {2}",
            usingClipCount - useClippingMaskMaxCount,
            this._renderTextureCount,
            usingClipCount
          );
        }
        for (let index = 0; index < this._clippingContextListForMask.getSize(); index++) {
          const clipContext = this._clippingContextListForMask.at(index);
          clipContext._layoutChannelIndex = 0;
          clipContext._layoutBounds.x = 0;
          clipContext._layoutBounds.y = 0;
          clipContext._layoutBounds.width = 1;
          clipContext._layoutBounds.height = 1;
          clipContext._bufferIndex = 0;
        }
        return;
      }
      const layoutCountMaxValue = this._renderTextureCount <= 1 ? 9 : 8;
      let countPerSheetDiv = usingClipCount / this._renderTextureCount;
      const reduceLayoutTextureCount = usingClipCount % this._renderTextureCount;
      countPerSheetDiv = Math.ceil(countPerSheetDiv);
      let divCount = countPerSheetDiv / ColorChannelCount;
      const modCount = countPerSheetDiv % ColorChannelCount;
      divCount = ~~divCount;
      let curClipIndex = 0;
      for (let renderTextureIndex = 0; renderTextureIndex < this._renderTextureCount; renderTextureIndex++) {
        for (let channelIndex = 0; channelIndex < ColorChannelCount; channelIndex++) {
          let layoutCount = divCount + (channelIndex < modCount ? 1 : 0);
          const checkChannelIndex = modCount + (divCount < 1 ? -1 : 0);
          if (channelIndex == checkChannelIndex && reduceLayoutTextureCount > 0) {
            layoutCount -= !(renderTextureIndex < reduceLayoutTextureCount) ? 1 : 0;
          }
          if (layoutCount == 0) {
          } else if (layoutCount == 1) {
            const clipContext = this._clippingContextListForMask.at(curClipIndex++);
            clipContext._layoutChannelIndex = channelIndex;
            clipContext._layoutBounds.x = 0;
            clipContext._layoutBounds.y = 0;
            clipContext._layoutBounds.width = 1;
            clipContext._layoutBounds.height = 1;
            clipContext._bufferIndex = renderTextureIndex;
          } else if (layoutCount == 2) {
            for (let i = 0; i < layoutCount; i++) {
              let xpos = i % 2;
              xpos = ~~xpos;
              const cc = this._clippingContextListForMask.at(
                curClipIndex++
              );
              cc._layoutChannelIndex = channelIndex;
              cc._layoutBounds.x = xpos * 0.5;
              cc._layoutBounds.y = 0;
              cc._layoutBounds.width = 0.5;
              cc._layoutBounds.height = 1;
              cc._bufferIndex = renderTextureIndex;
            }
          } else if (layoutCount <= 4) {
            for (let i = 0; i < layoutCount; i++) {
              let xpos = i % 2;
              let ypos = i / 2;
              xpos = ~~xpos;
              ypos = ~~ypos;
              const cc = this._clippingContextListForMask.at(curClipIndex++);
              cc._layoutChannelIndex = channelIndex;
              cc._layoutBounds.x = xpos * 0.5;
              cc._layoutBounds.y = ypos * 0.5;
              cc._layoutBounds.width = 0.5;
              cc._layoutBounds.height = 0.5;
              cc._bufferIndex = renderTextureIndex;
            }
          } else if (layoutCount <= layoutCountMaxValue) {
            for (let i = 0; i < layoutCount; i++) {
              let xpos = i % 3;
              let ypos = i / 3;
              xpos = ~~xpos;
              ypos = ~~ypos;
              const cc = this._clippingContextListForMask.at(
                curClipIndex++
              );
              cc._layoutChannelIndex = channelIndex;
              cc._layoutBounds.x = xpos / 3;
              cc._layoutBounds.y = ypos / 3;
              cc._layoutBounds.width = 1 / 3;
              cc._layoutBounds.height = 1 / 3;
              cc._bufferIndex = renderTextureIndex;
            }
          } else {
            CubismLogError(
              "not supported mask count : {0}\n[Details] render texture count : {1}, mask count : {2}",
              usingClipCount - useClippingMaskMaxCount,
              this._renderTextureCount,
              usingClipCount
            );
            for (let index = 0; index < layoutCount; index++) {
              const cc = this._clippingContextListForMask.at(
                curClipIndex++
              );
              cc._layoutChannelIndex = 0;
              cc._layoutBounds.x = 0;
              cc._layoutBounds.y = 0;
              cc._layoutBounds.width = 1;
              cc._layoutBounds.height = 1;
              cc._bufferIndex = 0;
            }
          }
        }
      }
    }
    /**
     * マスクされる描画オブジェクト群全体を囲む矩形（モデル座標系）を計算する
     * @param model モデルのインスタンス
     * @param clippingContext クリッピングマスクのコンテキスト
     */
    calcClippedDrawTotalBounds(model, clippingContext) {
      let clippedDrawTotalMinX = Number.MAX_VALUE;
      let clippedDrawTotalMinY = Number.MAX_VALUE;
      let clippedDrawTotalMaxX = Number.MIN_VALUE;
      let clippedDrawTotalMaxY = Number.MIN_VALUE;
      const clippedDrawCount = clippingContext._clippedDrawableIndexList.length;
      for (let clippedDrawableIndex = 0; clippedDrawableIndex < clippedDrawCount; clippedDrawableIndex++) {
        const drawableIndex = clippingContext._clippedDrawableIndexList[clippedDrawableIndex];
        const drawableVertexCount = model.getDrawableVertexCount(drawableIndex);
        const drawableVertexes = model.getDrawableVertices(drawableIndex);
        let minX = Number.MAX_VALUE;
        let minY = Number.MAX_VALUE;
        let maxX = -Number.MAX_VALUE;
        let maxY = -Number.MAX_VALUE;
        const loop = drawableVertexCount * Constant.vertexStep;
        for (let pi = Constant.vertexOffset; pi < loop; pi += Constant.vertexStep) {
          const x = drawableVertexes[pi];
          const y = drawableVertexes[pi + 1];
          if (x < minX) {
            minX = x;
          }
          if (x > maxX) {
            maxX = x;
          }
          if (y < minY) {
            minY = y;
          }
          if (y > maxY) {
            maxY = y;
          }
        }
        if (minX == Number.MAX_VALUE) {
          continue;
        }
        if (minX < clippedDrawTotalMinX) {
          clippedDrawTotalMinX = minX;
        }
        if (minY < clippedDrawTotalMinY) {
          clippedDrawTotalMinY = minY;
        }
        if (maxX > clippedDrawTotalMaxX) {
          clippedDrawTotalMaxX = maxX;
        }
        if (maxY > clippedDrawTotalMaxY) {
          clippedDrawTotalMaxY = maxY;
        }
        if (clippedDrawTotalMinX == Number.MAX_VALUE) {
          clippingContext._allClippedDrawRect.x = 0;
          clippingContext._allClippedDrawRect.y = 0;
          clippingContext._allClippedDrawRect.width = 0;
          clippingContext._allClippedDrawRect.height = 0;
          clippingContext._isUsing = false;
        } else {
          clippingContext._isUsing = true;
          const w = clippedDrawTotalMaxX - clippedDrawTotalMinX;
          const h = clippedDrawTotalMaxY - clippedDrawTotalMinY;
          clippingContext._allClippedDrawRect.x = clippedDrawTotalMinX;
          clippingContext._allClippedDrawRect.y = clippedDrawTotalMinY;
          clippingContext._allClippedDrawRect.width = w;
          clippingContext._allClippedDrawRect.height = h;
        }
      }
    }
    /**
     * 画面描画に使用するクリッピングマスクのリストを取得する
     * @return 画面描画に使用するクリッピングマスクのリスト
     */
    getClippingContextListForDraw() {
      return this._clippingContextListForDraw;
    }
    /**
     * クリッピングマスクバッファのサイズを取得する
     * @return クリッピングマスクバッファのサイズ
     */
    getClippingMaskBufferSize() {
      return this._clippingMaskBufferSize;
    }
    /**
     * このバッファのレンダーテクスチャの枚数を取得する
     * @return このバッファのレンダーテクスチャの枚数
     */
    getRenderTextureCount() {
      return this._renderTextureCount;
    }
    /**
     * カラーチャンネル（RGBA）のフラグを取得する
     * @param channelNo カラーチャンネル（RGBA）の番号（0:R, 1:G, 2:B, 3:A）
     */
    getChannelFlagAsColor(channelNo) {
      return this._channelColors.at(channelNo);
    }
    /**
     * クリッピングマスクバッファのサイズを設定する
     * @param size クリッピングマスクバッファのサイズ
     */
    setClippingMaskBufferSize(size) {
      this._clippingMaskBufferSize = size;
    }
  };

  // .trellis/workspace/lapp-runtime-src/src/renderer/WebSDK/Framework/src/rendering/cubismshader_webgl.ts
  var s_instance2;
  var ShaderCount = 10;
  var CubismShader_WebGL = class _CubismShader_WebGL {
    /**
     * privateなコンストラクタ
     */
    constructor() {
      __publicField(this, "_shaderSets");
      // ロードしたシェーダープログラムを保持する変数
      __publicField(this, "gl");
      this._shaderSets = new csmVector();
    }
    /**
     * インスタンスを取得する（シングルトン）
     * @return インスタンス
     */
    static getInstance() {
      if (s_instance2 == null) {
        s_instance2 = new _CubismShader_WebGL();
        return s_instance2;
      }
      return s_instance2;
    }
    /**
     * インスタンスを開放する（シングルトン）
     */
    static deleteInstance() {
      if (s_instance2) {
        s_instance2.release();
        s_instance2 = null;
      }
    }
    /**
     * デストラクタ相当の処理
     */
    release() {
      this.releaseShaderProgram();
    }
    /**
     * 描画用のシェーダプログラムの一連のセットアップを実行する
     * @param renderer レンダラー
     * @param model 描画対象のモデル
     * @param index 描画対象のメッシュのインデックス
     */
    setupShaderProgramForDraw(renderer, model, index) {
      if (!renderer.isPremultipliedAlpha()) {
        CubismLogError("NoPremultipliedAlpha is not allowed");
      }
      if (this._shaderSets.getSize() == 0) {
        this.generateShaders();
      }
      let srcColor;
      let dstColor;
      let srcAlpha;
      let dstAlpha;
      const masked = renderer.getClippingContextBufferForDraw() != null;
      const invertedMask = model.getDrawableInvertedMaskBit(index);
      const offset = masked ? invertedMask ? 2 : 1 : 0;
      let shaderSet;
      switch (model.getDrawableBlendMode(index)) {
        case 0 /* CubismBlendMode_Normal */:
        default:
          shaderSet = this._shaderSets.at(
            1 /* ShaderNames_NormalPremultipliedAlpha */ + offset
          );
          srcColor = this.gl.ONE;
          dstColor = this.gl.ONE_MINUS_SRC_ALPHA;
          srcAlpha = this.gl.ONE;
          dstAlpha = this.gl.ONE_MINUS_SRC_ALPHA;
          break;
        case 1 /* CubismBlendMode_Additive */:
          shaderSet = this._shaderSets.at(
            4 /* ShaderNames_AddPremultipliedAlpha */ + offset
          );
          srcColor = this.gl.ONE;
          dstColor = this.gl.ONE;
          srcAlpha = this.gl.ZERO;
          dstAlpha = this.gl.ONE;
          break;
        case 2 /* CubismBlendMode_Multiplicative */:
          shaderSet = this._shaderSets.at(
            7 /* ShaderNames_MultPremultipliedAlpha */ + offset
          );
          srcColor = this.gl.DST_COLOR;
          dstColor = this.gl.ONE_MINUS_SRC_ALPHA;
          srcAlpha = this.gl.ZERO;
          dstAlpha = this.gl.ONE;
          break;
      }
      this.gl.useProgram(shaderSet.shaderProgram);
      if (renderer._bufferData.vertex == null) {
        renderer._bufferData.vertex = this.gl.createBuffer();
      }
      this.gl.bindBuffer(this.gl.ARRAY_BUFFER, renderer._bufferData.vertex);
      const vertexArray = model.getDrawableVertices(index);
      this.gl.bufferData(this.gl.ARRAY_BUFFER, vertexArray, this.gl.DYNAMIC_DRAW);
      this.gl.enableVertexAttribArray(shaderSet.attributePositionLocation);
      this.gl.vertexAttribPointer(
        shaderSet.attributePositionLocation,
        2,
        this.gl.FLOAT,
        false,
        0,
        0
      );
      if (renderer._bufferData.uv == null) {
        renderer._bufferData.uv = this.gl.createBuffer();
      }
      this.gl.bindBuffer(this.gl.ARRAY_BUFFER, renderer._bufferData.uv);
      const uvArray = model.getDrawableVertexUvs(index);
      this.gl.bufferData(this.gl.ARRAY_BUFFER, uvArray, this.gl.DYNAMIC_DRAW);
      this.gl.enableVertexAttribArray(shaderSet.attributeTexCoordLocation);
      this.gl.vertexAttribPointer(
        shaderSet.attributeTexCoordLocation,
        2,
        this.gl.FLOAT,
        false,
        0,
        0
      );
      if (masked) {
        this.gl.activeTexture(this.gl.TEXTURE1);
        const tex = renderer.getClippingContextBufferForDraw().getClippingManager().getColorBuffer().at(renderer.getClippingContextBufferForDraw()._bufferIndex);
        this.gl.bindTexture(this.gl.TEXTURE_2D, tex);
        this.gl.uniform1i(shaderSet.samplerTexture1Location, 1);
        this.gl.uniformMatrix4fv(
          shaderSet.uniformClipMatrixLocation,
          false,
          renderer.getClippingContextBufferForDraw()._matrixForDraw.getArray()
        );
        const channelIndex = renderer.getClippingContextBufferForDraw()._layoutChannelIndex;
        const colorChannel = renderer.getClippingContextBufferForDraw().getClippingManager().getChannelFlagAsColor(channelIndex);
        this.gl.uniform4f(
          shaderSet.uniformChannelFlagLocation,
          colorChannel.r,
          colorChannel.g,
          colorChannel.b,
          colorChannel.a
        );
      }
      const textureNo = model.getDrawableTextureIndex(index);
      const textureId = renderer.getBindedTextures().getValue(textureNo);
      this.gl.activeTexture(this.gl.TEXTURE0);
      this.gl.bindTexture(this.gl.TEXTURE_2D, textureId);
      this.gl.uniform1i(shaderSet.samplerTexture0Location, 0);
      const matrix4x4 = renderer.getMvpMatrix();
      this.gl.uniformMatrix4fv(
        shaderSet.uniformMatrixLocation,
        false,
        matrix4x4.getArray()
      );
      const baseColor = renderer.getModelColorWithOpacity(
        model.getDrawableOpacity(index)
      );
      const multiplyColor = model.getMultiplyColor(index);
      const screenColor = model.getScreenColor(index);
      this.gl.uniform4f(
        shaderSet.uniformBaseColorLocation,
        baseColor.r,
        baseColor.g,
        baseColor.b,
        baseColor.a
      );
      this.gl.uniform4f(
        shaderSet.uniformMultiplyColorLocation,
        multiplyColor.r,
        multiplyColor.g,
        multiplyColor.b,
        multiplyColor.a
      );
      this.gl.uniform4f(
        shaderSet.uniformScreenColorLocation,
        screenColor.r,
        screenColor.g,
        screenColor.b,
        screenColor.a
      );
      if (renderer._bufferData.index == null) {
        renderer._bufferData.index = this.gl.createBuffer();
      }
      const indexArray = model.getDrawableVertexIndices(index);
      this.gl.bindBuffer(
        this.gl.ELEMENT_ARRAY_BUFFER,
        renderer._bufferData.index
      );
      this.gl.bufferData(
        this.gl.ELEMENT_ARRAY_BUFFER,
        indexArray,
        this.gl.DYNAMIC_DRAW
      );
      this.gl.blendFuncSeparate(srcColor, dstColor, srcAlpha, dstAlpha);
    }
    /**
     * マスク用のシェーダプログラムの一連のセットアップを実行する
     * @param renderer レンダラー
     * @param model 描画対象のモデル
     * @param index 描画対象のメッシュのインデックス
     */
    setupShaderProgramForMask(renderer, model, index) {
      if (!renderer.isPremultipliedAlpha()) {
        CubismLogError("NoPremultipliedAlpha is not allowed");
      }
      if (this._shaderSets.getSize() == 0) {
        this.generateShaders();
      }
      const shaderSet = this._shaderSets.at(
        0 /* ShaderNames_SetupMask */
      );
      this.gl.useProgram(shaderSet.shaderProgram);
      if (renderer._bufferData.vertex == null) {
        renderer._bufferData.vertex = this.gl.createBuffer();
      }
      this.gl.bindBuffer(this.gl.ARRAY_BUFFER, renderer._bufferData.vertex);
      const vertexArray = model.getDrawableVertices(index);
      this.gl.bufferData(this.gl.ARRAY_BUFFER, vertexArray, this.gl.DYNAMIC_DRAW);
      this.gl.enableVertexAttribArray(shaderSet.attributePositionLocation);
      this.gl.vertexAttribPointer(
        shaderSet.attributePositionLocation,
        2,
        this.gl.FLOAT,
        false,
        0,
        0
      );
      if (renderer._bufferData.uv == null) {
        renderer._bufferData.uv = this.gl.createBuffer();
      }
      this.gl.bindBuffer(this.gl.ARRAY_BUFFER, renderer._bufferData.uv);
      const textureNo = model.getDrawableTextureIndex(index);
      const textureId = renderer.getBindedTextures().getValue(textureNo);
      this.gl.activeTexture(this.gl.TEXTURE0);
      this.gl.bindTexture(this.gl.TEXTURE_2D, textureId);
      this.gl.uniform1i(shaderSet.samplerTexture0Location, 0);
      if (renderer._bufferData.uv == null) {
        renderer._bufferData.uv = this.gl.createBuffer();
      }
      this.gl.bindBuffer(this.gl.ARRAY_BUFFER, renderer._bufferData.uv);
      const uvArray = model.getDrawableVertexUvs(index);
      this.gl.bufferData(this.gl.ARRAY_BUFFER, uvArray, this.gl.DYNAMIC_DRAW);
      this.gl.enableVertexAttribArray(shaderSet.attributeTexCoordLocation);
      this.gl.vertexAttribPointer(
        shaderSet.attributeTexCoordLocation,
        2,
        this.gl.FLOAT,
        false,
        0,
        0
      );
      const context = renderer.getClippingContextBufferForMask();
      const channelIndex = renderer.getClippingContextBufferForMask()._layoutChannelIndex;
      const colorChannel = renderer.getClippingContextBufferForMask().getClippingManager().getChannelFlagAsColor(channelIndex);
      this.gl.uniform4f(
        shaderSet.uniformChannelFlagLocation,
        colorChannel.r,
        colorChannel.g,
        colorChannel.b,
        colorChannel.a
      );
      this.gl.uniformMatrix4fv(
        shaderSet.uniformClipMatrixLocation,
        false,
        renderer.getClippingContextBufferForMask()._matrixForMask.getArray()
      );
      const rect = renderer.getClippingContextBufferForMask()._layoutBounds;
      this.gl.uniform4f(
        shaderSet.uniformBaseColorLocation,
        rect.x * 2 - 1,
        rect.y * 2 - 1,
        rect.getRight() * 2 - 1,
        rect.getBottom() * 2 - 1
      );
      const multiplyColor = model.getMultiplyColor(index);
      const screenColor = model.getScreenColor(index);
      this.gl.uniform4f(
        shaderSet.uniformMultiplyColorLocation,
        multiplyColor.r,
        multiplyColor.g,
        multiplyColor.b,
        multiplyColor.a
      );
      this.gl.uniform4f(
        shaderSet.uniformScreenColorLocation,
        screenColor.r,
        screenColor.g,
        screenColor.b,
        screenColor.a
      );
      const srcColor = this.gl.ZERO;
      const dstColor = this.gl.ONE_MINUS_SRC_COLOR;
      const srcAlpha = this.gl.ZERO;
      const dstAlpha = this.gl.ONE_MINUS_SRC_ALPHA;
      if (renderer._bufferData.index == null) {
        renderer._bufferData.index = this.gl.createBuffer();
      }
      const indexArray = model.getDrawableVertexIndices(index);
      this.gl.bindBuffer(
        this.gl.ELEMENT_ARRAY_BUFFER,
        renderer._bufferData.index
      );
      this.gl.bufferData(
        this.gl.ELEMENT_ARRAY_BUFFER,
        indexArray,
        this.gl.DYNAMIC_DRAW
      );
      this.gl.blendFuncSeparate(srcColor, dstColor, srcAlpha, dstAlpha);
    }
    /**
     * シェーダープログラムを解放する
     */
    releaseShaderProgram() {
      for (let i = 0; i < this._shaderSets.getSize(); i++) {
        this.gl.deleteProgram(this._shaderSets.at(i).shaderProgram);
        this._shaderSets.at(i).shaderProgram = 0;
        this._shaderSets.set(i, void 0);
        this._shaderSets.set(i, null);
      }
    }
    /**
     * シェーダープログラムを初期化する
     * @param vertShaderSrc 頂点シェーダのソース
     * @param fragShaderSrc フラグメントシェーダのソース
     */
    generateShaders() {
      for (let i = 0; i < ShaderCount; i++) {
        this._shaderSets.pushBack(new CubismShaderSet());
      }
      this._shaderSets.at(0).shaderProgram = this.loadShaderProgram(
        vertexShaderSrcSetupMask,
        fragmentShaderSrcsetupMask
      );
      this._shaderSets.at(1).shaderProgram = this.loadShaderProgram(
        vertexShaderSrc,
        fragmentShaderSrcPremultipliedAlpha
      );
      this._shaderSets.at(2).shaderProgram = this.loadShaderProgram(
        vertexShaderSrcMasked,
        fragmentShaderSrcMaskPremultipliedAlpha
      );
      this._shaderSets.at(3).shaderProgram = this.loadShaderProgram(
        vertexShaderSrcMasked,
        fragmentShaderSrcMaskInvertedPremultipliedAlpha
      );
      this._shaderSets.at(4).shaderProgram = this._shaderSets.at(1).shaderProgram;
      this._shaderSets.at(5).shaderProgram = this._shaderSets.at(2).shaderProgram;
      this._shaderSets.at(6).shaderProgram = this._shaderSets.at(3).shaderProgram;
      this._shaderSets.at(7).shaderProgram = this._shaderSets.at(1).shaderProgram;
      this._shaderSets.at(8).shaderProgram = this._shaderSets.at(2).shaderProgram;
      this._shaderSets.at(9).shaderProgram = this._shaderSets.at(3).shaderProgram;
      this._shaderSets.at(0).attributePositionLocation = this.gl.getAttribLocation(
        this._shaderSets.at(0).shaderProgram,
        "a_position"
      );
      this._shaderSets.at(0).attributeTexCoordLocation = this.gl.getAttribLocation(
        this._shaderSets.at(0).shaderProgram,
        "a_texCoord"
      );
      this._shaderSets.at(0).samplerTexture0Location = this.gl.getUniformLocation(
        this._shaderSets.at(0).shaderProgram,
        "s_texture0"
      );
      this._shaderSets.at(0).uniformClipMatrixLocation = this.gl.getUniformLocation(
        this._shaderSets.at(0).shaderProgram,
        "u_clipMatrix"
      );
      this._shaderSets.at(0).uniformChannelFlagLocation = this.gl.getUniformLocation(
        this._shaderSets.at(0).shaderProgram,
        "u_channelFlag"
      );
      this._shaderSets.at(0).uniformBaseColorLocation = this.gl.getUniformLocation(
        this._shaderSets.at(0).shaderProgram,
        "u_baseColor"
      );
      this._shaderSets.at(0).uniformMultiplyColorLocation = this.gl.getUniformLocation(
        this._shaderSets.at(0).shaderProgram,
        "u_multiplyColor"
      );
      this._shaderSets.at(0).uniformScreenColorLocation = this.gl.getUniformLocation(
        this._shaderSets.at(0).shaderProgram,
        "u_screenColor"
      );
      this._shaderSets.at(1).attributePositionLocation = this.gl.getAttribLocation(
        this._shaderSets.at(1).shaderProgram,
        "a_position"
      );
      this._shaderSets.at(1).attributeTexCoordLocation = this.gl.getAttribLocation(
        this._shaderSets.at(1).shaderProgram,
        "a_texCoord"
      );
      this._shaderSets.at(1).samplerTexture0Location = this.gl.getUniformLocation(
        this._shaderSets.at(1).shaderProgram,
        "s_texture0"
      );
      this._shaderSets.at(1).uniformMatrixLocation = this.gl.getUniformLocation(
        this._shaderSets.at(1).shaderProgram,
        "u_matrix"
      );
      this._shaderSets.at(1).uniformBaseColorLocation = this.gl.getUniformLocation(
        this._shaderSets.at(1).shaderProgram,
        "u_baseColor"
      );
      this._shaderSets.at(1).uniformMultiplyColorLocation = this.gl.getUniformLocation(
        this._shaderSets.at(1).shaderProgram,
        "u_multiplyColor"
      );
      this._shaderSets.at(1).uniformScreenColorLocation = this.gl.getUniformLocation(
        this._shaderSets.at(1).shaderProgram,
        "u_screenColor"
      );
      this._shaderSets.at(2).attributePositionLocation = this.gl.getAttribLocation(
        this._shaderSets.at(2).shaderProgram,
        "a_position"
      );
      this._shaderSets.at(2).attributeTexCoordLocation = this.gl.getAttribLocation(
        this._shaderSets.at(2).shaderProgram,
        "a_texCoord"
      );
      this._shaderSets.at(2).samplerTexture0Location = this.gl.getUniformLocation(
        this._shaderSets.at(2).shaderProgram,
        "s_texture0"
      );
      this._shaderSets.at(2).samplerTexture1Location = this.gl.getUniformLocation(
        this._shaderSets.at(2).shaderProgram,
        "s_texture1"
      );
      this._shaderSets.at(2).uniformMatrixLocation = this.gl.getUniformLocation(
        this._shaderSets.at(2).shaderProgram,
        "u_matrix"
      );
      this._shaderSets.at(2).uniformClipMatrixLocation = this.gl.getUniformLocation(
        this._shaderSets.at(2).shaderProgram,
        "u_clipMatrix"
      );
      this._shaderSets.at(2).uniformChannelFlagLocation = this.gl.getUniformLocation(
        this._shaderSets.at(2).shaderProgram,
        "u_channelFlag"
      );
      this._shaderSets.at(2).uniformBaseColorLocation = this.gl.getUniformLocation(
        this._shaderSets.at(2).shaderProgram,
        "u_baseColor"
      );
      this._shaderSets.at(2).uniformMultiplyColorLocation = this.gl.getUniformLocation(
        this._shaderSets.at(2).shaderProgram,
        "u_multiplyColor"
      );
      this._shaderSets.at(2).uniformScreenColorLocation = this.gl.getUniformLocation(
        this._shaderSets.at(2).shaderProgram,
        "u_screenColor"
      );
      this._shaderSets.at(3).attributePositionLocation = this.gl.getAttribLocation(
        this._shaderSets.at(3).shaderProgram,
        "a_position"
      );
      this._shaderSets.at(3).attributeTexCoordLocation = this.gl.getAttribLocation(
        this._shaderSets.at(3).shaderProgram,
        "a_texCoord"
      );
      this._shaderSets.at(3).samplerTexture0Location = this.gl.getUniformLocation(
        this._shaderSets.at(3).shaderProgram,
        "s_texture0"
      );
      this._shaderSets.at(3).samplerTexture1Location = this.gl.getUniformLocation(
        this._shaderSets.at(3).shaderProgram,
        "s_texture1"
      );
      this._shaderSets.at(3).uniformMatrixLocation = this.gl.getUniformLocation(
        this._shaderSets.at(3).shaderProgram,
        "u_matrix"
      );
      this._shaderSets.at(3).uniformClipMatrixLocation = this.gl.getUniformLocation(
        this._shaderSets.at(3).shaderProgram,
        "u_clipMatrix"
      );
      this._shaderSets.at(3).uniformChannelFlagLocation = this.gl.getUniformLocation(
        this._shaderSets.at(3).shaderProgram,
        "u_channelFlag"
      );
      this._shaderSets.at(3).uniformBaseColorLocation = this.gl.getUniformLocation(
        this._shaderSets.at(3).shaderProgram,
        "u_baseColor"
      );
      this._shaderSets.at(3).uniformMultiplyColorLocation = this.gl.getUniformLocation(
        this._shaderSets.at(3).shaderProgram,
        "u_multiplyColor"
      );
      this._shaderSets.at(3).uniformScreenColorLocation = this.gl.getUniformLocation(
        this._shaderSets.at(3).shaderProgram,
        "u_screenColor"
      );
      this._shaderSets.at(4).attributePositionLocation = this.gl.getAttribLocation(
        this._shaderSets.at(4).shaderProgram,
        "a_position"
      );
      this._shaderSets.at(4).attributeTexCoordLocation = this.gl.getAttribLocation(
        this._shaderSets.at(4).shaderProgram,
        "a_texCoord"
      );
      this._shaderSets.at(4).samplerTexture0Location = this.gl.getUniformLocation(
        this._shaderSets.at(4).shaderProgram,
        "s_texture0"
      );
      this._shaderSets.at(4).uniformMatrixLocation = this.gl.getUniformLocation(
        this._shaderSets.at(4).shaderProgram,
        "u_matrix"
      );
      this._shaderSets.at(4).uniformBaseColorLocation = this.gl.getUniformLocation(
        this._shaderSets.at(4).shaderProgram,
        "u_baseColor"
      );
      this._shaderSets.at(4).uniformMultiplyColorLocation = this.gl.getUniformLocation(
        this._shaderSets.at(4).shaderProgram,
        "u_multiplyColor"
      );
      this._shaderSets.at(4).uniformScreenColorLocation = this.gl.getUniformLocation(
        this._shaderSets.at(4).shaderProgram,
        "u_screenColor"
      );
      this._shaderSets.at(5).attributePositionLocation = this.gl.getAttribLocation(
        this._shaderSets.at(5).shaderProgram,
        "a_position"
      );
      this._shaderSets.at(5).attributeTexCoordLocation = this.gl.getAttribLocation(
        this._shaderSets.at(5).shaderProgram,
        "a_texCoord"
      );
      this._shaderSets.at(5).samplerTexture0Location = this.gl.getUniformLocation(
        this._shaderSets.at(5).shaderProgram,
        "s_texture0"
      );
      this._shaderSets.at(5).samplerTexture1Location = this.gl.getUniformLocation(
        this._shaderSets.at(5).shaderProgram,
        "s_texture1"
      );
      this._shaderSets.at(5).uniformMatrixLocation = this.gl.getUniformLocation(
        this._shaderSets.at(5).shaderProgram,
        "u_matrix"
      );
      this._shaderSets.at(5).uniformClipMatrixLocation = this.gl.getUniformLocation(
        this._shaderSets.at(5).shaderProgram,
        "u_clipMatrix"
      );
      this._shaderSets.at(5).uniformChannelFlagLocation = this.gl.getUniformLocation(
        this._shaderSets.at(5).shaderProgram,
        "u_channelFlag"
      );
      this._shaderSets.at(5).uniformBaseColorLocation = this.gl.getUniformLocation(
        this._shaderSets.at(5).shaderProgram,
        "u_baseColor"
      );
      this._shaderSets.at(5).uniformMultiplyColorLocation = this.gl.getUniformLocation(
        this._shaderSets.at(5).shaderProgram,
        "u_multiplyColor"
      );
      this._shaderSets.at(5).uniformScreenColorLocation = this.gl.getUniformLocation(
        this._shaderSets.at(5).shaderProgram,
        "u_screenColor"
      );
      this._shaderSets.at(6).attributePositionLocation = this.gl.getAttribLocation(
        this._shaderSets.at(6).shaderProgram,
        "a_position"
      );
      this._shaderSets.at(6).attributeTexCoordLocation = this.gl.getAttribLocation(
        this._shaderSets.at(6).shaderProgram,
        "a_texCoord"
      );
      this._shaderSets.at(6).samplerTexture0Location = this.gl.getUniformLocation(
        this._shaderSets.at(6).shaderProgram,
        "s_texture0"
      );
      this._shaderSets.at(6).samplerTexture1Location = this.gl.getUniformLocation(
        this._shaderSets.at(6).shaderProgram,
        "s_texture1"
      );
      this._shaderSets.at(6).uniformMatrixLocation = this.gl.getUniformLocation(
        this._shaderSets.at(6).shaderProgram,
        "u_matrix"
      );
      this._shaderSets.at(6).uniformClipMatrixLocation = this.gl.getUniformLocation(
        this._shaderSets.at(6).shaderProgram,
        "u_clipMatrix"
      );
      this._shaderSets.at(6).uniformChannelFlagLocation = this.gl.getUniformLocation(
        this._shaderSets.at(6).shaderProgram,
        "u_channelFlag"
      );
      this._shaderSets.at(6).uniformBaseColorLocation = this.gl.getUniformLocation(
        this._shaderSets.at(6).shaderProgram,
        "u_baseColor"
      );
      this._shaderSets.at(6).uniformMultiplyColorLocation = this.gl.getUniformLocation(
        this._shaderSets.at(6).shaderProgram,
        "u_multiplyColor"
      );
      this._shaderSets.at(6).uniformScreenColorLocation = this.gl.getUniformLocation(
        this._shaderSets.at(6).shaderProgram,
        "u_screenColor"
      );
      this._shaderSets.at(7).attributePositionLocation = this.gl.getAttribLocation(
        this._shaderSets.at(7).shaderProgram,
        "a_position"
      );
      this._shaderSets.at(7).attributeTexCoordLocation = this.gl.getAttribLocation(
        this._shaderSets.at(7).shaderProgram,
        "a_texCoord"
      );
      this._shaderSets.at(7).samplerTexture0Location = this.gl.getUniformLocation(
        this._shaderSets.at(7).shaderProgram,
        "s_texture0"
      );
      this._shaderSets.at(7).uniformMatrixLocation = this.gl.getUniformLocation(
        this._shaderSets.at(7).shaderProgram,
        "u_matrix"
      );
      this._shaderSets.at(7).uniformBaseColorLocation = this.gl.getUniformLocation(
        this._shaderSets.at(7).shaderProgram,
        "u_baseColor"
      );
      this._shaderSets.at(7).uniformMultiplyColorLocation = this.gl.getUniformLocation(
        this._shaderSets.at(7).shaderProgram,
        "u_multiplyColor"
      );
      this._shaderSets.at(7).uniformScreenColorLocation = this.gl.getUniformLocation(
        this._shaderSets.at(7).shaderProgram,
        "u_screenColor"
      );
      this._shaderSets.at(8).attributePositionLocation = this.gl.getAttribLocation(
        this._shaderSets.at(8).shaderProgram,
        "a_position"
      );
      this._shaderSets.at(8).attributeTexCoordLocation = this.gl.getAttribLocation(
        this._shaderSets.at(8).shaderProgram,
        "a_texCoord"
      );
      this._shaderSets.at(8).samplerTexture0Location = this.gl.getUniformLocation(
        this._shaderSets.at(8).shaderProgram,
        "s_texture0"
      );
      this._shaderSets.at(8).samplerTexture1Location = this.gl.getUniformLocation(
        this._shaderSets.at(8).shaderProgram,
        "s_texture1"
      );
      this._shaderSets.at(8).uniformMatrixLocation = this.gl.getUniformLocation(
        this._shaderSets.at(8).shaderProgram,
        "u_matrix"
      );
      this._shaderSets.at(8).uniformClipMatrixLocation = this.gl.getUniformLocation(
        this._shaderSets.at(8).shaderProgram,
        "u_clipMatrix"
      );
      this._shaderSets.at(8).uniformChannelFlagLocation = this.gl.getUniformLocation(
        this._shaderSets.at(8).shaderProgram,
        "u_channelFlag"
      );
      this._shaderSets.at(8).uniformBaseColorLocation = this.gl.getUniformLocation(
        this._shaderSets.at(8).shaderProgram,
        "u_baseColor"
      );
      this._shaderSets.at(8).uniformMultiplyColorLocation = this.gl.getUniformLocation(
        this._shaderSets.at(8).shaderProgram,
        "u_multiplyColor"
      );
      this._shaderSets.at(8).uniformScreenColorLocation = this.gl.getUniformLocation(
        this._shaderSets.at(8).shaderProgram,
        "u_screenColor"
      );
      this._shaderSets.at(9).attributePositionLocation = this.gl.getAttribLocation(
        this._shaderSets.at(9).shaderProgram,
        "a_position"
      );
      this._shaderSets.at(9).attributeTexCoordLocation = this.gl.getAttribLocation(
        this._shaderSets.at(9).shaderProgram,
        "a_texCoord"
      );
      this._shaderSets.at(9).samplerTexture0Location = this.gl.getUniformLocation(
        this._shaderSets.at(9).shaderProgram,
        "s_texture0"
      );
      this._shaderSets.at(9).samplerTexture1Location = this.gl.getUniformLocation(
        this._shaderSets.at(9).shaderProgram,
        "s_texture1"
      );
      this._shaderSets.at(9).uniformMatrixLocation = this.gl.getUniformLocation(
        this._shaderSets.at(9).shaderProgram,
        "u_matrix"
      );
      this._shaderSets.at(9).uniformClipMatrixLocation = this.gl.getUniformLocation(
        this._shaderSets.at(9).shaderProgram,
        "u_clipMatrix"
      );
      this._shaderSets.at(9).uniformChannelFlagLocation = this.gl.getUniformLocation(
        this._shaderSets.at(9).shaderProgram,
        "u_channelFlag"
      );
      this._shaderSets.at(9).uniformBaseColorLocation = this.gl.getUniformLocation(
        this._shaderSets.at(9).shaderProgram,
        "u_baseColor"
      );
      this._shaderSets.at(9).uniformMultiplyColorLocation = this.gl.getUniformLocation(
        this._shaderSets.at(9).shaderProgram,
        "u_multiplyColor"
      );
      this._shaderSets.at(9).uniformScreenColorLocation = this.gl.getUniformLocation(
        this._shaderSets.at(9).shaderProgram,
        "u_screenColor"
      );
    }
    /**
     * シェーダプログラムをロードしてアドレスを返す
     * @param vertexShaderSource    頂点シェーダのソース
     * @param fragmentShaderSource  フラグメントシェーダのソース
     * @return シェーダプログラムのアドレス
     */
    loadShaderProgram(vertexShaderSource, fragmentShaderSource) {
      let shaderProgram = this.gl.createProgram();
      let vertShader = this.compileShaderSource(
        this.gl.VERTEX_SHADER,
        vertexShaderSource
      );
      if (!vertShader) {
        CubismLogError("Vertex shader compile error!");
        return 0;
      }
      let fragShader = this.compileShaderSource(
        this.gl.FRAGMENT_SHADER,
        fragmentShaderSource
      );
      if (!fragShader) {
        CubismLogError("Vertex shader compile error!");
        return 0;
      }
      this.gl.attachShader(shaderProgram, vertShader);
      this.gl.attachShader(shaderProgram, fragShader);
      this.gl.linkProgram(shaderProgram);
      const linkStatus = this.gl.getProgramParameter(
        shaderProgram,
        this.gl.LINK_STATUS
      );
      if (!linkStatus) {
        CubismLogError("Failed to link program: {0}", shaderProgram);
        this.gl.deleteShader(vertShader);
        vertShader = 0;
        this.gl.deleteShader(fragShader);
        fragShader = 0;
        if (shaderProgram) {
          this.gl.deleteProgram(shaderProgram);
          shaderProgram = 0;
        }
        return 0;
      }
      this.gl.deleteShader(vertShader);
      this.gl.deleteShader(fragShader);
      return shaderProgram;
    }
    /**
     * シェーダープログラムをコンパイルする
     * @param shaderType シェーダタイプ(Vertex/Fragment)
     * @param shaderSource シェーダソースコード
     *
     * @return コンパイルされたシェーダープログラム
     */
    compileShaderSource(shaderType, shaderSource) {
      const source = shaderSource;
      const shader = this.gl.createShader(shaderType);
      this.gl.shaderSource(shader, source);
      this.gl.compileShader(shader);
      if (!shader) {
        const log = this.gl.getShaderInfoLog(shader);
        CubismLogError("Shader compile log: {0} ", log);
      }
      const status = this.gl.getShaderParameter(
        shader,
        this.gl.COMPILE_STATUS
      );
      if (!status) {
        this.gl.deleteShader(shader);
        return null;
      }
      return shader;
    }
    setGl(gl2) {
      this.gl = gl2;
    }
    // webglコンテキスト
  };
  var CubismShaderSet = class {
    constructor() {
      __publicField(this, "shaderProgram");
      // シェーダープログラムのアドレス
      __publicField(this, "attributePositionLocation");
      // シェーダープログラムに渡す変数のアドレス（Position）
      __publicField(this, "attributeTexCoordLocation");
      // シェーダープログラムに渡す変数のアドレス（TexCoord）
      __publicField(this, "uniformMatrixLocation");
      // シェーダープログラムに渡す変数のアドレス（Matrix）
      __publicField(this, "uniformClipMatrixLocation");
      // シェーダープログラムに渡す変数のアドレス（ClipMatrix）
      __publicField(this, "samplerTexture0Location");
      // シェーダープログラムに渡す変数のアドレス（Texture0）
      __publicField(this, "samplerTexture1Location");
      // シェーダープログラムに渡す変数のアドレス（Texture1）
      __publicField(this, "uniformBaseColorLocation");
      // シェーダープログラムに渡す変数のアドレス（BaseColor）
      __publicField(this, "uniformChannelFlagLocation");
      // シェーダープログラムに渡す変数のアドレス（ChannelFlag）
      __publicField(this, "uniformMultiplyColorLocation");
      // シェーダープログラムに渡す変数のアドレス（MultiplyColor）
      __publicField(this, "uniformScreenColorLocation");
    }
    // シェーダープログラムに渡す変数のアドレス（ScreenColor）
  };
  var ShaderNames = /* @__PURE__ */ ((ShaderNames2) => {
    ShaderNames2[ShaderNames2["ShaderNames_SetupMask"] = 0] = "ShaderNames_SetupMask";
    ShaderNames2[ShaderNames2["ShaderNames_NormalPremultipliedAlpha"] = 1] = "ShaderNames_NormalPremultipliedAlpha";
    ShaderNames2[ShaderNames2["ShaderNames_NormalMaskedPremultipliedAlpha"] = 2] = "ShaderNames_NormalMaskedPremultipliedAlpha";
    ShaderNames2[ShaderNames2["ShaderNames_NomralMaskedInvertedPremultipliedAlpha"] = 3] = "ShaderNames_NomralMaskedInvertedPremultipliedAlpha";
    ShaderNames2[ShaderNames2["ShaderNames_AddPremultipliedAlpha"] = 4] = "ShaderNames_AddPremultipliedAlpha";
    ShaderNames2[ShaderNames2["ShaderNames_AddMaskedPremultipliedAlpha"] = 5] = "ShaderNames_AddMaskedPremultipliedAlpha";
    ShaderNames2[ShaderNames2["ShaderNames_AddMaskedPremultipliedAlphaInverted"] = 6] = "ShaderNames_AddMaskedPremultipliedAlphaInverted";
    ShaderNames2[ShaderNames2["ShaderNames_MultPremultipliedAlpha"] = 7] = "ShaderNames_MultPremultipliedAlpha";
    ShaderNames2[ShaderNames2["ShaderNames_MultMaskedPremultipliedAlpha"] = 8] = "ShaderNames_MultMaskedPremultipliedAlpha";
    ShaderNames2[ShaderNames2["ShaderNames_MultMaskedPremultipliedAlphaInverted"] = 9] = "ShaderNames_MultMaskedPremultipliedAlphaInverted";
    return ShaderNames2;
  })(ShaderNames || {});
  var vertexShaderSrcSetupMask = "attribute vec4     a_position;attribute vec2     a_texCoord;varying vec2       v_texCoord;varying vec4       v_myPos;uniform mat4       u_clipMatrix;void main(){   gl_Position = u_clipMatrix * a_position;   v_myPos = u_clipMatrix * a_position;   v_texCoord = a_texCoord;   v_texCoord.y = 1.0 - v_texCoord.y;}";
  var fragmentShaderSrcsetupMask = "precision mediump float;varying vec2       v_texCoord;varying vec4       v_myPos;uniform vec4       u_baseColor;uniform vec4       u_channelFlag;uniform sampler2D  s_texture0;void main(){   float isInside =        step(u_baseColor.x, v_myPos.x/v_myPos.w)       * step(u_baseColor.y, v_myPos.y/v_myPos.w)       * step(v_myPos.x/v_myPos.w, u_baseColor.z)       * step(v_myPos.y/v_myPos.w, u_baseColor.w);   gl_FragColor = u_channelFlag * texture2D(s_texture0, v_texCoord).a * isInside;}";
  var vertexShaderSrc = "attribute vec4     a_position;attribute vec2     a_texCoord;varying vec2       v_texCoord;uniform mat4       u_matrix;void main(){   gl_Position = u_matrix * a_position;   v_texCoord = a_texCoord;   v_texCoord.y = 1.0 - v_texCoord.y;}";
  var vertexShaderSrcMasked = "attribute vec4     a_position;attribute vec2     a_texCoord;varying vec2       v_texCoord;varying vec4       v_clipPos;uniform mat4       u_matrix;uniform mat4       u_clipMatrix;void main(){   gl_Position = u_matrix * a_position;   v_clipPos = u_clipMatrix * a_position;   v_texCoord = a_texCoord;   v_texCoord.y = 1.0 - v_texCoord.y;}";
  var fragmentShaderSrcPremultipliedAlpha = "precision mediump float;varying vec2       v_texCoord;uniform vec4       u_baseColor;uniform sampler2D  s_texture0;uniform vec4       u_multiplyColor;uniform vec4       u_screenColor;void main(){   vec4 texColor = texture2D(s_texture0, v_texCoord);   texColor.rgb = texColor.rgb * u_multiplyColor.rgb;   texColor.rgb = (texColor.rgb + u_screenColor.rgb * texColor.a) - (texColor.rgb * u_screenColor.rgb);   vec4 color = texColor * u_baseColor;   gl_FragColor = vec4(color.rgb, color.a);}";
  var fragmentShaderSrcMaskPremultipliedAlpha = "precision mediump float;varying vec2       v_texCoord;varying vec4       v_clipPos;uniform vec4       u_baseColor;uniform vec4       u_channelFlag;uniform sampler2D  s_texture0;uniform sampler2D  s_texture1;uniform vec4       u_multiplyColor;uniform vec4       u_screenColor;void main(){   vec4 texColor = texture2D(s_texture0, v_texCoord);   texColor.rgb = texColor.rgb * u_multiplyColor.rgb;   texColor.rgb = (texColor.rgb + u_screenColor.rgb * texColor.a) - (texColor.rgb * u_screenColor.rgb);   vec4 col_formask = texColor * u_baseColor;   vec4 clipMask = (1.0 - texture2D(s_texture1, v_clipPos.xy / v_clipPos.w)) * u_channelFlag;   float maskVal = clipMask.r + clipMask.g + clipMask.b + clipMask.a;   col_formask = col_formask * maskVal;   gl_FragColor = col_formask;}";
  var fragmentShaderSrcMaskInvertedPremultipliedAlpha = "precision mediump float;varying vec2      v_texCoord;varying vec4      v_clipPos;uniform sampler2D s_texture0;uniform sampler2D s_texture1;uniform vec4      u_channelFlag;uniform vec4      u_baseColor;uniform vec4      u_multiplyColor;uniform vec4      u_screenColor;void main(){   vec4 texColor = texture2D(s_texture0, v_texCoord);   texColor.rgb = texColor.rgb * u_multiplyColor.rgb;   texColor.rgb = (texColor.rgb + u_screenColor.rgb * texColor.a) - (texColor.rgb * u_screenColor.rgb);   vec4 col_formask = texColor * u_baseColor;   vec4 clipMask = (1.0 - texture2D(s_texture1, v_clipPos.xy / v_clipPos.w)) * u_channelFlag;   float maskVal = clipMask.r + clipMask.g + clipMask.b + clipMask.a;   col_formask = col_formask * (1.0 - maskVal);   gl_FragColor = col_formask;}";
  var Live2DCubismFramework34;
  ((Live2DCubismFramework42) => {
    Live2DCubismFramework42.CubismShaderSet = CubismShaderSet;
    Live2DCubismFramework42.CubismShader_WebGL = CubismShader_WebGL;
    Live2DCubismFramework42.ShaderNames = ShaderNames;
  })(Live2DCubismFramework34 || (Live2DCubismFramework34 = {}));

  // .trellis/workspace/lapp-runtime-src/src/renderer/WebSDK/Framework/src/rendering/cubismrenderer_webgl.ts
  var s_viewport;
  var s_fbo;
  var CubismClippingManager_WebGL = class extends CubismClippingManager {
    /**
     * コンストラクタ
     */
    constructor() {
      super(CubismClippingContext_WebGL);
      __publicField(this, "_currentMaskRenderTexture");
      // マスク用レンダーテクスチャのアドレス
      __publicField(this, "_maskRenderTextures");
      // レンダーテクスチャのリスト
      __publicField(this, "_maskColorBuffers");
      // マスク用カラーバッファーのアドレスのリスト
      __publicField(this, "_currentFrameNo");
      // マスクテクスチャに与えるフレーム番号
      __publicField(this, "_maskTexture");
      // マスク用のテクスチャリソースのリスト
      __publicField(this, "gl");
    }
    /**
     * テンポラリのレンダーテクスチャのアドレスを取得する
     * FrameBufferObjectが存在しない場合、新しく生成する
     *
     * @return レンダーテクスチャの配列
     */
    getMaskRenderTexture() {
      if (this._maskTexture && this._maskTexture.textures != null) {
        this._maskTexture.frameNo = this._currentFrameNo;
      } else {
        if (this._maskRenderTextures != null) {
          this._maskRenderTextures.clear();
        }
        this._maskRenderTextures = new csmVector();
        if (this._maskColorBuffers != null) {
          this._maskColorBuffers.clear();
        }
        this._maskColorBuffers = new csmVector();
        const size = this._clippingMaskBufferSize;
        for (let index = 0; index < this._renderTextureCount; index++) {
          this._maskColorBuffers.pushBack(this.gl.createTexture());
          this.gl.bindTexture(
            this.gl.TEXTURE_2D,
            this._maskColorBuffers.at(index)
          );
          this.gl.texImage2D(
            this.gl.TEXTURE_2D,
            0,
            this.gl.RGBA,
            size,
            size,
            0,
            this.gl.RGBA,
            this.gl.UNSIGNED_BYTE,
            null
          );
          this.gl.texParameteri(
            this.gl.TEXTURE_2D,
            this.gl.TEXTURE_WRAP_S,
            this.gl.CLAMP_TO_EDGE
          );
          this.gl.texParameteri(
            this.gl.TEXTURE_2D,
            this.gl.TEXTURE_WRAP_T,
            this.gl.CLAMP_TO_EDGE
          );
          this.gl.texParameteri(
            this.gl.TEXTURE_2D,
            this.gl.TEXTURE_MIN_FILTER,
            this.gl.LINEAR
          );
          this.gl.texParameteri(
            this.gl.TEXTURE_2D,
            this.gl.TEXTURE_MAG_FILTER,
            this.gl.LINEAR
          );
          this.gl.bindTexture(this.gl.TEXTURE_2D, null);
          this._maskRenderTextures.pushBack(this.gl.createFramebuffer());
          this.gl.bindFramebuffer(
            this.gl.FRAMEBUFFER,
            this._maskRenderTextures.at(index)
          );
          this.gl.framebufferTexture2D(
            this.gl.FRAMEBUFFER,
            this.gl.COLOR_ATTACHMENT0,
            this.gl.TEXTURE_2D,
            this._maskColorBuffers.at(index),
            0
          );
        }
        this.gl.bindFramebuffer(this.gl.FRAMEBUFFER, s_fbo);
        this._maskTexture = new CubismRenderTextureResource(
          this._currentFrameNo,
          this._maskRenderTextures
        );
      }
      return this._maskTexture.textures;
    }
    /**
     * WebGLレンダリングコンテキストを設定する
     * @param gl WebGLレンダリングコンテキスト
     */
    setGL(gl2) {
      this.gl = gl2;
    }
    /**
     * クリッピングコンテキストを作成する。モデル描画時に実行する。
     * @param model モデルのインスタンス
     * @param renderer レンダラのインスタンス
     */
    setupClippingContext(model, renderer) {
      this._currentFrameNo++;
      let usingClipCount = 0;
      for (let clipIndex = 0; clipIndex < this._clippingContextListForMask.getSize(); clipIndex++) {
        const cc = this._clippingContextListForMask.at(clipIndex);
        this.calcClippedDrawTotalBounds(model, cc);
        if (cc._isUsing) {
          usingClipCount++;
        }
      }
      if (usingClipCount > 0) {
        this.gl.viewport(
          0,
          0,
          this._clippingMaskBufferSize,
          this._clippingMaskBufferSize
        );
        this._currentMaskRenderTexture = this.getMaskRenderTexture().at(0);
        renderer.preDraw();
        this.setupLayoutBounds(usingClipCount);
        this.gl.bindFramebuffer(
          this.gl.FRAMEBUFFER,
          this._currentMaskRenderTexture
        );
        if (this._clearedFrameBufferFlags.getSize() != this._renderTextureCount) {
          this._clearedFrameBufferFlags.clear();
          this._clearedFrameBufferFlags = new csmVector(
            this._renderTextureCount
          );
        }
        for (let index = 0; index < this._clearedFrameBufferFlags.getSize(); index++) {
          this._clearedFrameBufferFlags.set(index, false);
        }
        for (let clipIndex = 0; clipIndex < this._clippingContextListForMask.getSize(); clipIndex++) {
          const clipContext = this._clippingContextListForMask.at(clipIndex);
          const allClipedDrawRect = clipContext._allClippedDrawRect;
          const layoutBoundsOnTex01 = clipContext._layoutBounds;
          const margin = 0.05;
          let scaleX = 0;
          let scaleY = 0;
          const clipContextRenderTexture = this.getMaskRenderTexture().at(
            clipContext._bufferIndex
          );
          if (this._currentMaskRenderTexture != clipContextRenderTexture) {
            this._currentMaskRenderTexture = clipContextRenderTexture;
            renderer.preDraw();
            this.gl.bindFramebuffer(
              this.gl.FRAMEBUFFER,
              this._currentMaskRenderTexture
            );
          }
          this._tmpBoundsOnModel.setRect(allClipedDrawRect);
          this._tmpBoundsOnModel.expand(
            allClipedDrawRect.width * margin,
            allClipedDrawRect.height * margin
          );
          scaleX = layoutBoundsOnTex01.width / this._tmpBoundsOnModel.width;
          scaleY = layoutBoundsOnTex01.height / this._tmpBoundsOnModel.height;
          {
            this._tmpMatrix.loadIdentity();
            {
              this._tmpMatrix.translateRelative(-1, -1);
              this._tmpMatrix.scaleRelative(2, 2);
            }
            {
              this._tmpMatrix.translateRelative(
                layoutBoundsOnTex01.x,
                layoutBoundsOnTex01.y
              );
              this._tmpMatrix.scaleRelative(scaleX, scaleY);
              this._tmpMatrix.translateRelative(
                -this._tmpBoundsOnModel.x,
                -this._tmpBoundsOnModel.y
              );
            }
            this._tmpMatrixForMask.setMatrix(this._tmpMatrix.getArray());
          }
          {
            this._tmpMatrix.loadIdentity();
            {
              this._tmpMatrix.translateRelative(
                layoutBoundsOnTex01.x,
                layoutBoundsOnTex01.y
              );
              this._tmpMatrix.scaleRelative(scaleX, scaleY);
              this._tmpMatrix.translateRelative(
                -this._tmpBoundsOnModel.x,
                -this._tmpBoundsOnModel.y
              );
            }
            this._tmpMatrixForDraw.setMatrix(this._tmpMatrix.getArray());
          }
          clipContext._matrixForMask.setMatrix(this._tmpMatrixForMask.getArray());
          clipContext._matrixForDraw.setMatrix(this._tmpMatrixForDraw.getArray());
          const clipDrawCount = clipContext._clippingIdCount;
          for (let i = 0; i < clipDrawCount; i++) {
            const clipDrawIndex = clipContext._clippingIdList[i];
            if (!model.getDrawableDynamicFlagVertexPositionsDidChange(clipDrawIndex)) {
              continue;
            }
            renderer.setIsCulling(
              model.getDrawableCulling(clipDrawIndex) != false
            );
            if (!this._clearedFrameBufferFlags.at(clipContext._bufferIndex)) {
              this.gl.clearColor(1, 1, 1, 1);
              this.gl.clear(this.gl.COLOR_BUFFER_BIT);
              this._clearedFrameBufferFlags.set(clipContext._bufferIndex, true);
            }
            renderer.setClippingContextBufferForMask(clipContext);
            renderer.drawMeshWebGL(model, clipDrawIndex);
          }
        }
        this.gl.bindFramebuffer(this.gl.FRAMEBUFFER, s_fbo);
        renderer.setClippingContextBufferForMask(null);
        this.gl.viewport(
          s_viewport[0],
          s_viewport[1],
          s_viewport[2],
          s_viewport[3]
        );
      }
    }
    /**
     * カラーバッファを取得する
     * @return カラーバッファ
     */
    getColorBuffer() {
      return this._maskColorBuffers;
    }
    /**
     * マスクの合計数をカウント
     * @returns
     */
    getClippingMaskCount() {
      return this._clippingContextListForMask.getSize();
    }
    // WebGLレンダリングコンテキスト
  };
  var CubismRenderTextureResource = class {
    /**
     * 引数付きコンストラクタ
     * @param frameNo レンダラーのフレーム番号
     * @param texture テクスチャのアドレス
     */
    constructor(frameNo, texture) {
      __publicField(this, "frameNo");
      // レンダラのフレーム番号
      __publicField(this, "textures");
      this.frameNo = frameNo;
      this.textures = texture;
    }
    // テクスチャのアドレス
  };
  var CubismClippingContext_WebGL = class extends CubismClippingContext {
    /**
     * 引数付きコンストラクタ
     */
    constructor(manager, clippingDrawableIndices, clipCount) {
      super(clippingDrawableIndices, clipCount);
      __publicField(this, "_owner");
      this._owner = manager;
    }
    /**
     * このマスクを管理するマネージャのインスタンスを取得する
     * @return クリッピングマネージャのインスタンス
     */
    getClippingManager() {
      return this._owner;
    }
    setGl(gl2) {
      this._owner.setGL(gl2);
    }
    // このマスクを管理しているマネージャのインスタンス
  };
  var CubismRendererProfile_WebGL = class {
    constructor() {
      __publicField(this, "_lastArrayBufferBinding");
      ///< モデル描画直前の頂点バッファ
      __publicField(this, "_lastElementArrayBufferBinding");
      ///< モデル描画直前のElementバッファ
      __publicField(this, "_lastProgram");
      ///< モデル描画直前のシェーダプログラムバッファ
      __publicField(this, "_lastActiveTexture");
      ///< モデル描画直前のアクティブなテクスチャ
      __publicField(this, "_lastTexture0Binding2D");
      ///< モデル描画直前のテクスチャユニット0
      __publicField(this, "_lastTexture1Binding2D");
      ///< モデル描画直前のテクスチャユニット1
      __publicField(this, "_lastVertexAttribArrayEnabled");
      ///< モデル描画直前のテクスチャユニット1
      __publicField(this, "_lastScissorTest");
      ///< モデル描画直前のGL_VERTEX_ATTRIB_ARRAY_ENABLEDパラメータ
      __publicField(this, "_lastBlend");
      ///< モデル描画直前のGL_SCISSOR_TESTパラメータ
      __publicField(this, "_lastStencilTest");
      ///< モデル描画直前のGL_STENCIL_TESTパラメータ
      __publicField(this, "_lastDepthTest");
      ///< モデル描画直前のGL_DEPTH_TESTパラメータ
      __publicField(this, "_lastCullFace");
      ///< モデル描画直前のGL_CULL_FACEパラメータ
      __publicField(this, "_lastFrontFace");
      ///< モデル描画直前のGL_CULL_FACEパラメータ
      __publicField(this, "_lastColorMask");
      ///< モデル描画直前のGL_COLOR_WRITEMASKパラメータ
      __publicField(this, "_lastBlending");
      ///< モデル描画直前のカラーブレンディングパラメータ
      __publicField(this, "_lastFBO");
      ///< モデル描画直前のフレームバッファ
      __publicField(this, "_lastViewport");
      ///< モデル描画直前のビューポート
      __publicField(this, "gl");
      this._lastVertexAttribArrayEnabled = new Array(4);
      this._lastColorMask = new Array(4);
      this._lastBlending = new Array(4);
      this._lastViewport = new Array(4);
    }
    setGlEnable(index, enabled) {
      if (enabled) this.gl.enable(index);
      else this.gl.disable(index);
    }
    setGlEnableVertexAttribArray(index, enabled) {
      if (enabled) this.gl.enableVertexAttribArray(index);
      else this.gl.disableVertexAttribArray(index);
    }
    save() {
      if (this.gl == null) {
        CubismLogError(
          "'gl' is null. WebGLRenderingContext is required.\nPlease call 'CubimRenderer_WebGL.startUp' function."
        );
        return;
      }
      this._lastArrayBufferBinding = this.gl.getParameter(
        this.gl.ARRAY_BUFFER_BINDING
      );
      this._lastElementArrayBufferBinding = this.gl.getParameter(
        this.gl.ELEMENT_ARRAY_BUFFER_BINDING
      );
      this._lastProgram = this.gl.getParameter(this.gl.CURRENT_PROGRAM);
      this._lastActiveTexture = this.gl.getParameter(this.gl.ACTIVE_TEXTURE);
      this.gl.activeTexture(this.gl.TEXTURE1);
      this._lastTexture1Binding2D = this.gl.getParameter(
        this.gl.TEXTURE_BINDING_2D
      );
      this.gl.activeTexture(this.gl.TEXTURE0);
      this._lastTexture0Binding2D = this.gl.getParameter(
        this.gl.TEXTURE_BINDING_2D
      );
      this._lastVertexAttribArrayEnabled[0] = this.gl.getVertexAttrib(
        0,
        this.gl.VERTEX_ATTRIB_ARRAY_ENABLED
      );
      this._lastVertexAttribArrayEnabled[1] = this.gl.getVertexAttrib(
        1,
        this.gl.VERTEX_ATTRIB_ARRAY_ENABLED
      );
      this._lastVertexAttribArrayEnabled[2] = this.gl.getVertexAttrib(
        2,
        this.gl.VERTEX_ATTRIB_ARRAY_ENABLED
      );
      this._lastVertexAttribArrayEnabled[3] = this.gl.getVertexAttrib(
        3,
        this.gl.VERTEX_ATTRIB_ARRAY_ENABLED
      );
      this._lastScissorTest = this.gl.isEnabled(this.gl.SCISSOR_TEST);
      this._lastStencilTest = this.gl.isEnabled(this.gl.STENCIL_TEST);
      this._lastDepthTest = this.gl.isEnabled(this.gl.DEPTH_TEST);
      this._lastCullFace = this.gl.isEnabled(this.gl.CULL_FACE);
      this._lastBlend = this.gl.isEnabled(this.gl.BLEND);
      this._lastFrontFace = this.gl.getParameter(this.gl.FRONT_FACE);
      this._lastColorMask = this.gl.getParameter(this.gl.COLOR_WRITEMASK);
      this._lastBlending[0] = this.gl.getParameter(this.gl.BLEND_SRC_RGB);
      this._lastBlending[1] = this.gl.getParameter(this.gl.BLEND_DST_RGB);
      this._lastBlending[2] = this.gl.getParameter(this.gl.BLEND_SRC_ALPHA);
      this._lastBlending[3] = this.gl.getParameter(this.gl.BLEND_DST_ALPHA);
      this._lastFBO = this.gl.getParameter(this.gl.FRAMEBUFFER_BINDING);
      this._lastViewport = this.gl.getParameter(this.gl.VIEWPORT);
    }
    restore() {
      if (this.gl == null) {
        CubismLogError(
          "'gl' is null. WebGLRenderingContext is required.\nPlease call 'CubimRenderer_WebGL.startUp' function."
        );
        return;
      }
      this.gl.useProgram(this._lastProgram);
      this.setGlEnableVertexAttribArray(0, this._lastVertexAttribArrayEnabled[0]);
      this.setGlEnableVertexAttribArray(1, this._lastVertexAttribArrayEnabled[1]);
      this.setGlEnableVertexAttribArray(2, this._lastVertexAttribArrayEnabled[2]);
      this.setGlEnableVertexAttribArray(3, this._lastVertexAttribArrayEnabled[3]);
      this.setGlEnable(this.gl.SCISSOR_TEST, this._lastScissorTest);
      this.setGlEnable(this.gl.STENCIL_TEST, this._lastStencilTest);
      this.setGlEnable(this.gl.DEPTH_TEST, this._lastDepthTest);
      this.setGlEnable(this.gl.CULL_FACE, this._lastCullFace);
      this.setGlEnable(this.gl.BLEND, this._lastBlend);
      this.gl.frontFace(this._lastFrontFace);
      this.gl.colorMask(
        this._lastColorMask[0],
        this._lastColorMask[1],
        this._lastColorMask[2],
        this._lastColorMask[3]
      );
      this.gl.bindBuffer(this.gl.ARRAY_BUFFER, this._lastArrayBufferBinding);
      this.gl.bindBuffer(
        this.gl.ELEMENT_ARRAY_BUFFER,
        this._lastElementArrayBufferBinding
      );
      this.gl.activeTexture(this.gl.TEXTURE1);
      this.gl.bindTexture(this.gl.TEXTURE_2D, this._lastTexture1Binding2D);
      this.gl.activeTexture(this.gl.TEXTURE0);
      this.gl.bindTexture(this.gl.TEXTURE_2D, this._lastTexture0Binding2D);
      this.gl.activeTexture(this._lastActiveTexture);
      this.gl.blendFuncSeparate(
        this._lastBlending[0],
        this._lastBlending[1],
        this._lastBlending[2],
        this._lastBlending[3]
      );
    }
    setGl(gl2) {
      this.gl = gl2;
    }
  };
  var CubismRenderer_WebGL = class extends CubismRenderer {
    /**
     * コンストラクタ
     */
    constructor() {
      super();
      __publicField(this, "_textures");
      // モデルが参照するテクスチャとレンダラでバインドしているテクスチャとのマップ
      __publicField(this, "_sortedDrawableIndexList");
      // 描画オブジェクトのインデックスを描画順に並べたリスト
      __publicField(this, "_clippingManager");
      // クリッピングマスク管理オブジェクト
      __publicField(this, "_clippingContextBufferForMask");
      // マスクテクスチャに描画するためのクリッピングコンテキスト
      __publicField(this, "_clippingContextBufferForDraw");
      // 画面上描画するためのクリッピングコンテキスト
      __publicField(this, "_rendererProfile");
      __publicField(this, "firstDraw");
      __publicField(this, "_bufferData");
      // 頂点バッファデータ
      __publicField(this, "_extension");
      // 拡張機能
      __publicField(this, "gl");
      this._clippingContextBufferForMask = null;
      this._clippingContextBufferForDraw = null;
      this._rendererProfile = new CubismRendererProfile_WebGL();
      this.firstDraw = true;
      this._textures = new csmMap();
      this._sortedDrawableIndexList = new csmVector();
      this._bufferData = {
        vertex: WebGLBuffer = null,
        uv: WebGLBuffer = null,
        index: WebGLBuffer = null
      };
      this._textures.prepareCapacity(32, true);
    }
    /**
     * レンダラの初期化処理を実行する
     * 引数に渡したモデルからレンダラの初期化処理に必要な情報を取り出すことができる
     *
     * @param model モデルのインスタンス
     * @param maskBufferCount バッファの生成数
     */
    initialize(model, maskBufferCount = 1) {
      if (model.isUsingMasking()) {
        this._clippingManager = new CubismClippingManager_WebGL();
        this._clippingManager.initialize(model, maskBufferCount);
      }
      this._sortedDrawableIndexList.resize(model.getDrawableCount(), 0);
      super.initialize(model);
    }
    /**
     * WebGLテクスチャのバインド処理
     * CubismRendererにテクスチャを設定し、CubismRenderer内でその画像を参照するためのIndex値を戻り値とする
     * @param modelTextureNo セットするモデルテクスチャの番号
     * @param glTextureNo WebGLテクスチャの番号
     */
    bindTexture(modelTextureNo, glTexture) {
      this._textures.setValue(modelTextureNo, glTexture);
    }
    /**
     * WebGLにバインドされたテクスチャのリストを取得する
     * @return テクスチャのリスト
     */
    getBindedTextures() {
      return this._textures;
    }
    /**
     * クリッピングマスクバッファのサイズを設定する
     * マスク用のFrameBufferを破棄、再作成する為処理コストは高い
     * @param size クリッピングマスクバッファのサイズ
     */
    setClippingMaskBufferSize(size) {
      if (!this._model.isUsingMasking()) {
        return;
      }
      const renderTextureCount = this._clippingManager.getRenderTextureCount();
      this._clippingManager.release();
      this._clippingManager = void 0;
      this._clippingManager = null;
      this._clippingManager = new CubismClippingManager_WebGL();
      this._clippingManager.setClippingMaskBufferSize(size);
      this._clippingManager.initialize(
        this.getModel(),
        renderTextureCount
        // インスタンス破棄前に保存したレンダーテクスチャの数
      );
    }
    /**
     * クリッピングマスクバッファのサイズを取得する
     * @return クリッピングマスクバッファのサイズ
     */
    getClippingMaskBufferSize() {
      return this._model.isUsingMasking() ? this._clippingManager.getClippingMaskBufferSize() : -1;
    }
    /**
     * レンダーテクスチャの枚数を取得する
     * @return レンダーテクスチャの枚数
     */
    getRenderTextureCount() {
      return this._model.isUsingMasking() ? this._clippingManager.getRenderTextureCount() : -1;
    }
    /**
     * デストラクタ相当の処理
     */
    release() {
      if (this._clippingManager) {
        this._clippingManager.release();
        this._clippingManager = void 0;
        this._clippingManager = null;
      }
      if (this.gl == null) {
        return;
      }
      this.gl.deleteBuffer(this._bufferData.vertex);
      this._bufferData.vertex = null;
      this.gl.deleteBuffer(this._bufferData.uv);
      this._bufferData.uv = null;
      this.gl.deleteBuffer(this._bufferData.index);
      this._bufferData.index = null;
      this._bufferData = null;
      this._textures = null;
    }
    /**
     * モデルを描画する実際の処理
     */
    doDrawModel() {
      if (this.gl == null) {
        CubismLogError(
          "'gl' is null. WebGLRenderingContext is required.\nPlease call 'CubimRenderer_WebGL.startUp' function."
        );
        return;
      }
      if (this._clippingManager != null) {
        this.preDraw();
        if (this.isUsingHighPrecisionMask()) {
          this._clippingManager.setupMatrixForHighPrecision(
            this.getModel(),
            false
          );
        } else {
          this._clippingManager.setupClippingContext(this.getModel(), this);
        }
      }
      this.preDraw();
      const drawableCount = this.getModel().getDrawableCount();
      const renderOrder = this.getModel().getDrawableRenderOrders();
      for (let i = 0; i < drawableCount; ++i) {
        const order = renderOrder[i];
        this._sortedDrawableIndexList.set(order, i);
      }
      for (let i = 0; i < drawableCount; ++i) {
        const drawableIndex = this._sortedDrawableIndexList.at(i);
        if (!this.getModel().getDrawableDynamicFlagIsVisible(drawableIndex)) {
          continue;
        }
        const clipContext = this._clippingManager != null ? this._clippingManager.getClippingContextListForDraw().at(drawableIndex) : null;
        if (clipContext != null && this.isUsingHighPrecisionMask()) {
          if (clipContext._isUsing) {
            this.gl.viewport(
              0,
              0,
              this._clippingManager.getClippingMaskBufferSize(),
              this._clippingManager.getClippingMaskBufferSize()
            );
            this.preDraw();
            this.gl.bindFramebuffer(
              this.gl.FRAMEBUFFER,
              clipContext.getClippingManager().getMaskRenderTexture().at(clipContext._bufferIndex)
            );
            this.gl.clearColor(1, 1, 1, 1);
            this.gl.clear(this.gl.COLOR_BUFFER_BIT);
          }
          {
            const clipDrawCount = clipContext._clippingIdCount;
            for (let index = 0; index < clipDrawCount; index++) {
              const clipDrawIndex = clipContext._clippingIdList[index];
              if (!this._model.getDrawableDynamicFlagVertexPositionsDidChange(
                clipDrawIndex
              )) {
                continue;
              }
              this.setIsCulling(
                this._model.getDrawableCulling(clipDrawIndex) != false
              );
              this.setClippingContextBufferForMask(clipContext);
              this.drawMeshWebGL(this._model, clipDrawIndex);
            }
          }
          {
            this.gl.bindFramebuffer(this.gl.FRAMEBUFFER, s_fbo);
            this.setClippingContextBufferForMask(null);
            this.gl.viewport(
              s_viewport[0],
              s_viewport[1],
              s_viewport[2],
              s_viewport[3]
            );
            this.preDraw();
          }
        }
        this.setClippingContextBufferForDraw(clipContext);
        this.setIsCulling(this.getModel().getDrawableCulling(drawableIndex));
        this.drawMeshWebGL(this._model, drawableIndex);
      }
    }
    /**
     * 描画オブジェクト（アートメッシュ）を描画する。
     * @param model 描画対象のモデル
     * @param index 描画対象のメッシュのインデックス
     */
    drawMeshWebGL(model, index) {
      if (this.isCulling()) {
        this.gl.enable(this.gl.CULL_FACE);
      } else {
        this.gl.disable(this.gl.CULL_FACE);
      }
      this.gl.frontFace(this.gl.CCW);
      if (this.isGeneratingMask()) {
        CubismShader_WebGL.getInstance().setupShaderProgramForMask(
          this,
          model,
          index
        );
      } else {
        CubismShader_WebGL.getInstance().setupShaderProgramForDraw(
          this,
          model,
          index
        );
      }
      {
        const indexCount = model.getDrawableVertexIndexCount(index);
        this.gl.drawElements(
          this.gl.TRIANGLES,
          indexCount,
          this.gl.UNSIGNED_SHORT,
          0
        );
      }
      this.gl.useProgram(null);
      this.setClippingContextBufferForDraw(null);
      this.setClippingContextBufferForMask(null);
    }
    saveProfile() {
      this._rendererProfile.save();
    }
    restoreProfile() {
      this._rendererProfile.restore();
    }
    /**
     * レンダラが保持する静的なリソースを解放する
     * WebGLの静的なシェーダープログラムを解放する
     */
    static doStaticRelease() {
      CubismShader_WebGL.deleteInstance();
    }
    /**
     * レンダーステートを設定する
     * @param fbo アプリケーション側で指定しているフレームバッファ
     * @param viewport ビューポート
     */
    setRenderState(fbo, viewport) {
      s_fbo = fbo;
      s_viewport = viewport;
    }
    /**
     * 描画開始時の追加処理
     * モデルを描画する前にクリッピングマスクに必要な処理を実装している
     */
    preDraw() {
      if (this.firstDraw) {
        this.firstDraw = false;
      }
      this.gl.disable(this.gl.SCISSOR_TEST);
      this.gl.disable(this.gl.STENCIL_TEST);
      this.gl.disable(this.gl.DEPTH_TEST);
      this.gl.frontFace(this.gl.CW);
      this.gl.enable(this.gl.BLEND);
      this.gl.colorMask(true, true, true, true);
      this.gl.bindBuffer(this.gl.ARRAY_BUFFER, null);
      this.gl.bindBuffer(this.gl.ELEMENT_ARRAY_BUFFER, null);
      if (this.getAnisotropy() > 0 && this._extension) {
        for (let i = 0; i < this._textures.getSize(); ++i) {
          this.gl.bindTexture(this.gl.TEXTURE_2D, this._textures.getValue(i));
          this.gl.texParameterf(
            this.gl.TEXTURE_2D,
            this._extension.TEXTURE_MAX_ANISOTROPY_EXT,
            this.getAnisotropy()
          );
        }
      }
    }
    /**
     * マスクテクスチャに描画するクリッピングコンテキストをセットする
     */
    setClippingContextBufferForMask(clip) {
      this._clippingContextBufferForMask = clip;
    }
    /**
     * マスクテクスチャに描画するクリッピングコンテキストを取得する
     * @return マスクテクスチャに描画するクリッピングコンテキスト
     */
    getClippingContextBufferForMask() {
      return this._clippingContextBufferForMask;
    }
    /**
     * 画面上に描画するクリッピングコンテキストをセットする
     */
    setClippingContextBufferForDraw(clip) {
      this._clippingContextBufferForDraw = clip;
    }
    /**
     * 画面上に描画するクリッピングコンテキストを取得する
     * @return 画面上に描画するクリッピングコンテキスト
     */
    getClippingContextBufferForDraw() {
      return this._clippingContextBufferForDraw;
    }
    /**
     * マスク生成時かを判定する
     * @returns 判定値
     */
    isGeneratingMask() {
      return this.getClippingContextBufferForMask() != null;
    }
    /**
     * glの設定
     */
    startUp(gl2) {
      this.gl = gl2;
      if (this._clippingManager) {
        this._clippingManager.setGL(gl2);
      }
      CubismShader_WebGL.getInstance().setGl(gl2);
      this._rendererProfile.setGl(gl2);
      this._extension = this.gl.getExtension("EXT_texture_filter_anisotropic") || this.gl.getExtension("WEBKIT_EXT_texture_filter_anisotropic") || this.gl.getExtension("MOZ_EXT_texture_filter_anisotropic");
    }
    // webglコンテキスト
  };
  CubismRenderer.staticRelease = () => {
    CubismRenderer_WebGL.doStaticRelease();
  };
  var Live2DCubismFramework35;
  ((Live2DCubismFramework42) => {
    Live2DCubismFramework42.CubismClippingContext = CubismClippingContext_WebGL;
    Live2DCubismFramework42.CubismClippingManager_WebGL = CubismClippingManager_WebGL;
    Live2DCubismFramework42.CubismRenderTextureResource = CubismRenderTextureResource;
    Live2DCubismFramework42.CubismRenderer_WebGL = CubismRenderer_WebGL;
  })(Live2DCubismFramework35 || (Live2DCubismFramework35 = {}));

  // .trellis/workspace/lapp-runtime-src/src/renderer/WebSDK/Framework/src/model/cubismmodel.ts
  var DrawableColorData = class {
    constructor(isOverwritten = false, color = new CubismTextureColor()) {
      __publicField(this, "isOverwritten");
      __publicField(this, "color");
      this.isOverwritten = isOverwritten;
      this.color = color;
    }
  };
  var PartColorData = class {
    constructor(isOverwritten = false, color = new CubismTextureColor()) {
      __publicField(this, "isOverwritten");
      __publicField(this, "color");
      this.isOverwritten = isOverwritten;
      this.color = color;
    }
  };
  var DrawableCullingData = class {
    /**
     * コンストラクタ
     *
     * @param isOverwritten
     * @param isCulling
     */
    constructor(isOverwritten = false, isCulling = false) {
      __publicField(this, "isOverwritten");
      __publicField(this, "isCulling");
      this.isOverwritten = isOverwritten;
      this.isCulling = isCulling;
    }
  };
  var CubismModel = class {
    /**
     * コンストラクタ
     * @param model モデル
     */
    constructor(model) {
      __publicField(this, "_notExistPartOpacities");
      // 存在していないパーツの不透明度のリスト
      __publicField(this, "_notExistPartId");
      // 存在していないパーツIDのリスト
      __publicField(this, "_notExistParameterValues");
      // 存在していないパラメータの値のリスト
      __publicField(this, "_notExistParameterId");
      // 存在していないパラメータIDのリスト
      __publicField(this, "_savedParameters");
      // 保存されたパラメータ
      __publicField(this, "_isOverwrittenModelMultiplyColors");
      // SDK上でモデル全体の乗算色を上書きするか判定するフラグ
      __publicField(this, "_isOverwrittenModelScreenColors");
      // SDK上でモデル全体のスクリーン色を上書きするか判定するフラグ
      __publicField(this, "_userMultiplyColors");
      // Drawableごとに設定する乗算色と上書きフラグを管理するリスト
      __publicField(this, "_userScreenColors");
      // Drawableごとに設定するスクリーン色と上書きフラグを管理するリスト
      __publicField(this, "_userPartScreenColors");
      // Part 乗算色の配列
      __publicField(this, "_userPartMultiplyColors");
      // Part スクリーン色の配列
      __publicField(this, "_partChildDrawables");
      // Partの子DrawableIndexの配列
      __publicField(this, "_model");
      // モデル
      __publicField(this, "_parameterValues");
      // パラメータの値のリスト
      __publicField(this, "_parameterMaximumValues");
      // パラメータの最大値のリスト
      __publicField(this, "_parameterMinimumValues");
      // パラメータの最小値のリスト
      __publicField(this, "_partOpacities");
      // パーツの不透明度のリスト
      __publicField(this, "_modelOpacity");
      // モデルの不透明度
      __publicField(this, "_parameterIds");
      __publicField(this, "_partIds");
      __publicField(this, "_drawableIds");
      __publicField(this, "_isOverwrittenCullings");
      // モデルのカリング設定をすべて上書きするか？
      __publicField(this, "_userCullings");
      this._model = model;
      this._parameterValues = null;
      this._parameterMaximumValues = null;
      this._parameterMinimumValues = null;
      this._partOpacities = null;
      this._savedParameters = new csmVector();
      this._parameterIds = new csmVector();
      this._drawableIds = new csmVector();
      this._partIds = new csmVector();
      this._isOverwrittenModelMultiplyColors = false;
      this._isOverwrittenModelScreenColors = false;
      this._isOverwrittenCullings = false;
      this._modelOpacity = 1;
      this._userMultiplyColors = new csmVector();
      this._userScreenColors = new csmVector();
      this._userCullings = new csmVector();
      this._userPartMultiplyColors = new csmVector();
      this._userPartScreenColors = new csmVector();
      this._partChildDrawables = new csmVector();
      this._notExistPartId = new csmMap();
      this._notExistParameterId = new csmMap();
      this._notExistParameterValues = new csmMap();
      this._notExistPartOpacities = new csmMap();
    }
    /**
     * モデルのパラメータの更新
     */
    update() {
      this._model.update();
      this._model.drawables.resetDynamicFlags();
    }
    /**
     * PixelsPerUnitを取得する
     * @returns PixelsPerUnit
     */
    getPixelsPerUnit() {
      if (this._model == null) {
        return 0;
      }
      return this._model.canvasinfo.PixelsPerUnit;
    }
    /**
     * キャンバスの幅を取得する
     */
    getCanvasWidth() {
      if (this._model == null) {
        return 0;
      }
      return this._model.canvasinfo.CanvasWidth / this._model.canvasinfo.PixelsPerUnit;
    }
    /**
     * キャンバスの高さを取得する
     */
    getCanvasHeight() {
      if (this._model == null) {
        return 0;
      }
      return this._model.canvasinfo.CanvasHeight / this._model.canvasinfo.PixelsPerUnit;
    }
    /**
     * パラメータを保存する
     */
    saveParameters() {
      const parameterCount = this._model.parameters.count;
      const savedParameterCount = this._savedParameters.getSize();
      for (let i = 0; i < parameterCount; ++i) {
        if (i < savedParameterCount) {
          this._savedParameters.set(i, this._parameterValues[i]);
        } else {
          this._savedParameters.pushBack(this._parameterValues[i]);
        }
      }
    }
    /**
     * 乗算色を取得する
     * @param index Drawablesのインデックス
     * @returns 指定したdrawableの乗算色(RGBA)
     */
    getMultiplyColor(index) {
      if (this.getOverwriteFlagForModelMultiplyColors() || this.getOverwriteFlagForDrawableMultiplyColors(index)) {
        return this._userMultiplyColors.at(index).color;
      }
      const color = this.getDrawableMultiplyColor(index);
      return color;
    }
    /**
     * スクリーン色を取得する
     * @param index Drawablesのインデックス
     * @returns 指定したdrawableのスクリーン色(RGBA)
     */
    getScreenColor(index) {
      if (this.getOverwriteFlagForModelScreenColors() || this.getOverwriteFlagForDrawableScreenColors(index)) {
        return this._userScreenColors.at(index).color;
      }
      const color = this.getDrawableScreenColor(index);
      return color;
    }
    /**
     * 乗算色をセットする
     * @param index Drawablesのインデックス
     * @param color 設定する乗算色(CubismTextureColor)
     */
    setMultiplyColorByTextureColor(index, color) {
      this.setMultiplyColorByRGBA(index, color.r, color.g, color.b, color.a);
    }
    /**
     * 乗算色をセットする
     * @param index Drawablesのインデックス
     * @param r 設定する乗算色のR値
     * @param g 設定する乗算色のG値
     * @param b 設定する乗算色のB値
     * @param a 設定する乗算色のA値
     */
    setMultiplyColorByRGBA(index, r, g, b, a = 1) {
      this._userMultiplyColors.at(index).color.r = r;
      this._userMultiplyColors.at(index).color.g = g;
      this._userMultiplyColors.at(index).color.b = b;
      this._userMultiplyColors.at(index).color.a = a;
    }
    /**
     * スクリーン色をセットする
     * @param index Drawablesのインデックス
     * @param color 設定するスクリーン色(CubismTextureColor)
     */
    setScreenColorByTextureColor(index, color) {
      this.setScreenColorByRGBA(index, color.r, color.g, color.b, color.a);
    }
    /**
     * スクリーン色をセットする
     * @param index Drawablesのインデックス
     * @param r 設定するスクリーン色のR値
     * @param g 設定するスクリーン色のG値
     * @param b 設定するスクリーン色のB値
     * @param a 設定するスクリーン色のA値
     */
    setScreenColorByRGBA(index, r, g, b, a = 1) {
      this._userScreenColors.at(index).color.r = r;
      this._userScreenColors.at(index).color.g = g;
      this._userScreenColors.at(index).color.b = b;
      this._userScreenColors.at(index).color.a = a;
    }
    /**
     * partの乗算色を取得する
     * @param partIndex partのインデックス
     * @returns 指定したpartの乗算色
     */
    getPartMultiplyColor(partIndex) {
      return this._userPartMultiplyColors.at(partIndex).color;
    }
    /**
     * partのスクリーン色を取得する
     * @param partIndex partのインデックス
     * @returns 指定したpartのスクリーン色
     */
    getPartScreenColor(partIndex) {
      return this._userPartScreenColors.at(partIndex).color;
    }
    /**
     * partのOverwriteColor setter関数
     * @param partIndex partのインデックス
     * @param r 設定する色のR値
     * @param g 設定する色のG値
     * @param b 設定する色のB値
     * @param a 設定する色のA値
     * @param partColors 設定するpartのカラーデータ配列
     * @param drawableColors partに関連するDrawableのカラーデータ配列
     */
    setPartColor(partIndex, r, g, b, a, partColors, drawableColors) {
      partColors.at(partIndex).color.r = r;
      partColors.at(partIndex).color.g = g;
      partColors.at(partIndex).color.b = b;
      partColors.at(partIndex).color.a = a;
      if (partColors.at(partIndex).isOverwritten) {
        for (let i = 0; i < this._partChildDrawables.at(partIndex).getSize(); ++i) {
          const drawableIndex = this._partChildDrawables.at(partIndex).at(i);
          drawableColors.at(drawableIndex).color.r = r;
          drawableColors.at(drawableIndex).color.g = g;
          drawableColors.at(drawableIndex).color.b = b;
          drawableColors.at(drawableIndex).color.a = a;
        }
      }
    }
    /**
     * 乗算色をセットする
     * @param partIndex partのインデックス
     * @param color 設定する乗算色(CubismTextureColor)
     */
    setPartMultiplyColorByTextureColor(partIndex, color) {
      this.setPartMultiplyColorByRGBA(
        partIndex,
        color.r,
        color.g,
        color.b,
        color.a
      );
    }
    /**
     * 乗算色をセットする
     * @param partIndex partのインデックス
     * @param r 設定する乗算色のR値
     * @param g 設定する乗算色のG値
     * @param b 設定する乗算色のB値
     * @param a 設定する乗算色のA値
     */
    setPartMultiplyColorByRGBA(partIndex, r, g, b, a) {
      this.setPartColor(
        partIndex,
        r,
        g,
        b,
        a,
        this._userPartMultiplyColors,
        this._userMultiplyColors
      );
    }
    /**
     * スクリーン色をセットする
     * @param partIndex partのインデックス
     * @param color 設定するスクリーン色(CubismTextureColor)
     */
    setPartScreenColorByTextureColor(partIndex, color) {
      this.setPartScreenColorByRGBA(
        partIndex,
        color.r,
        color.g,
        color.b,
        color.a
      );
    }
    /**
     * スクリーン色をセットする
     * @param partIndex partのインデックス
     * @param r 設定するスクリーン色のR値
     * @param g 設定するスクリーン色のG値
     * @param b 設定するスクリーン色のB値
     * @param a 設定するスクリーン色のA値
     */
    setPartScreenColorByRGBA(partIndex, r, g, b, a) {
      this.setPartColor(
        partIndex,
        r,
        g,
        b,
        a,
        this._userPartScreenColors,
        this._userScreenColors
      );
    }
    /**
     * SDKから指定したモデルの乗算色を上書きするか
     * @returns true -> SDKからの情報を優先する
     *          false -> モデルに設定されている色情報を使用
     */
    getOverwriteFlagForModelMultiplyColors() {
      return this._isOverwrittenModelMultiplyColors;
    }
    /**
     * SDKから指定したモデルのスクリーン色を上書きするか
     * @returns true -> SDKからの情報を優先する
     *          false -> モデルに設定されている色情報を使用
     */
    getOverwriteFlagForModelScreenColors() {
      return this._isOverwrittenModelScreenColors;
    }
    /**
     * SDKから指定したモデルの乗算色を上書きするかセットする
     * @param value true -> SDKからの情報を優先する
     *              false -> モデルに設定されている色情報を使用
     */
    setOverwriteFlagForModelMultiplyColors(value) {
      this._isOverwrittenModelMultiplyColors = value;
    }
    /**
     * SDKから指定したモデルのスクリーン色を上書きするかセットする
     * @param value true -> SDKからの情報を優先する
     *              false -> モデルに設定されている色情報を使用
     */
    setOverwriteFlagForModelScreenColors(value) {
      this._isOverwrittenModelScreenColors = value;
    }
    /**
     * SDKから指定したDrawableIndexの乗算色を上書きするか
     * @returns true -> SDKからの情報を優先する
     *          false -> モデルに設定されている色情報を使用
     */
    getOverwriteFlagForDrawableMultiplyColors(drawableindex) {
      return this._userMultiplyColors.at(drawableindex).isOverwritten;
    }
    /**
     * SDKから指定したDrawableIndexのスクリーン色を上書きするか
     * @returns true -> SDKからの情報を優先する
     *          false -> モデルに設定されている色情報を使用
     */
    getOverwriteFlagForDrawableScreenColors(drawableindex) {
      return this._userScreenColors.at(drawableindex).isOverwritten;
    }
    /**
     * SDKから指定したDrawableIndexの乗算色を上書きするかセットする
     * @param value true -> SDKからの情報を優先する
     *              false -> モデルに設定されている色情報を使用
     */
    setOverwriteFlagForDrawableMultiplyColors(drawableindex, value) {
      this._userMultiplyColors.at(drawableindex).isOverwritten = value;
    }
    /**
     * SDKから指定したDrawableIndexのスクリーン色を上書きするかセットする
     * @param value true -> SDKからの情報を優先する
     *              false -> モデルに設定されている色情報を使用
     */
    setOverwriteFlagForDrawableScreenColors(drawableindex, value) {
      this._userScreenColors.at(drawableindex).isOverwritten = value;
    }
    /**
     * SDKからpartの乗算色を上書きするか
     * @param partIndex partのインデックス
     * @returns true    ->  SDKからの情報を優先する
     *          false   ->  モデルに設定されている色情報を使用
     */
    getOverwriteColorForPartMultiplyColors(partIndex) {
      return this._userPartMultiplyColors.at(partIndex).isOverwritten;
    }
    /**
     * SDKからpartのスクリーン色を上書きするか
     * @param partIndex partのインデックス
     * @returns true    ->  SDKからの情報を優先する
     *          false   ->  モデルに設定されている色情報を使用
     */
    getOverwriteColorForPartScreenColors(partIndex) {
      return this._userPartScreenColors.at(partIndex).isOverwritten;
    }
    /**
     * partのOverwriteFlag setter関数
     * @param partIndex partのインデックス
     * @param value true -> SDKからの情報を優先する
     *              false -> モデルに設定されている色情報を使用
     * @param partColors 設定するpartのカラーデータ配列
     * @param drawableColors partに関連するDrawableのカラーデータ配列
     */
    setOverwriteColorForPartColors(partIndex, value, partColors, drawableColors) {
      partColors.at(partIndex).isOverwritten = value;
      for (let i = 0; i < this._partChildDrawables.at(partIndex).getSize(); ++i) {
        const drawableIndex = this._partChildDrawables.at(partIndex).at(i);
        drawableColors.at(drawableIndex).isOverwritten = value;
        if (value) {
          drawableColors.at(drawableIndex).color.r = partColors.at(partIndex).color.r;
          drawableColors.at(drawableIndex).color.g = partColors.at(partIndex).color.g;
          drawableColors.at(drawableIndex).color.b = partColors.at(partIndex).color.b;
          drawableColors.at(drawableIndex).color.a = partColors.at(partIndex).color.a;
        }
      }
    }
    /**
     * SDKからpartのスクリーン色を上書きするかをセットする
     * @param partIndex partのインデックス
     * @param value true -> SDKからの情報を優先する
     *              false -> モデルに設定されている色情報を使用
     */
    setOverwriteColorForPartMultiplyColors(partIndex, value) {
      this._userPartMultiplyColors.at(partIndex).isOverwritten = value;
      this.setOverwriteColorForPartColors(
        partIndex,
        value,
        this._userPartMultiplyColors,
        this._userMultiplyColors
      );
    }
    /**
     * SDKからpartのスクリーン色を上書きするかをセットする
     * @param partIndex partのインデックス
     * @param value true -> SDKからの情報を優先する
     *              false -> モデルに設定されている色情報を使用
     */
    setOverwriteColorForPartScreenColors(partIndex, value) {
      this._userPartScreenColors.at(partIndex).isOverwritten = value;
      this.setOverwriteColorForPartColors(
        partIndex,
        value,
        this._userPartScreenColors,
        this._userScreenColors
      );
    }
    /**
     * Drawableのカリング情報を取得する。
     *
     * @param   drawableIndex   Drawableのインデックス
     * @return  Drawableのカリング情報
     */
    getDrawableCulling(drawableIndex) {
      if (this.getOverwriteFlagForModelCullings() || this.getOverwriteFlagForDrawableCullings(drawableIndex)) {
        return this._userCullings.at(drawableIndex).isCulling;
      }
      const constantFlags = this._model.drawables.constantFlags;
      return !Live2DCubismCore.Utils.hasIsDoubleSidedBit(
        constantFlags[drawableIndex]
      );
    }
    /**
     * Drawableのカリング情報を設定する。
     *
     * @param drawableIndex Drawableのインデックス
     * @param isCulling カリング情報
     */
    setDrawableCulling(drawableIndex, isCulling) {
      this._userCullings.at(drawableIndex).isCulling = isCulling;
    }
    /**
     * SDKからモデル全体のカリング設定を上書きするか。
     *
     * @retval  true    ->  SDK上のカリング設定を使用
     * @retval  false   ->  モデルのカリング設定を使用
     */
    getOverwriteFlagForModelCullings() {
      return this._isOverwrittenCullings;
    }
    /**
     * SDKからモデル全体のカリング設定を上書きするかを設定する。
     *
     * @param isOverwrittenCullings SDK上のカリング設定を使うならtrue、モデルのカリング設定を使うならfalse
     */
    setOverwriteFlagForModelCullings(isOverwrittenCullings) {
      this._isOverwrittenCullings = isOverwrittenCullings;
    }
    /**
     *
     * @param drawableIndex Drawableのインデックス
     * @retval  true    ->  SDK上のカリング設定を使用
     * @retval  false   ->  モデルのカリング設定を使用
     */
    getOverwriteFlagForDrawableCullings(drawableIndex) {
      return this._userCullings.at(drawableIndex).isOverwritten;
    }
    /**
     *
     * @param drawableIndex Drawableのインデックス
     * @param isOverwrittenCullings SDK上のカリング設定を使うならtrue、モデルのカリング設定を使うならfalse
     */
    setOverwriteFlagForDrawableCullings(drawableIndex, isOverwrittenCullings) {
      this._userCullings.at(drawableIndex).isOverwritten = isOverwrittenCullings;
    }
    /**
     * モデルの不透明度を取得する
     *
     * @returns 不透明度の値
     */
    getModelOapcity() {
      return this._modelOpacity;
    }
    /**
     * モデルの不透明度を設定する
     *
     * @param value 不透明度の値
     */
    setModelOapcity(value) {
      this._modelOpacity = value;
    }
    /**
     * モデルを取得
     */
    getModel() {
      return this._model;
    }
    /**
     * パーツのインデックスを取得
     * @param partId パーツのID
     * @return パーツのインデックス
     */
    getPartIndex(partId) {
      let partIndex;
      const partCount = this._model.parts.count;
      for (partIndex = 0; partIndex < partCount; ++partIndex) {
        if (partId == this._partIds.at(partIndex)) {
          return partIndex;
        }
      }
      if (this._notExistPartId.isExist(partId)) {
        return this._notExistPartId.getValue(partId);
      }
      partIndex = partCount + this._notExistPartId.getSize();
      this._notExistPartId.setValue(partId, partIndex);
      this._notExistPartOpacities.appendKey(partIndex);
      return partIndex;
    }
    /**
     * パーツのIDを取得する。
     *
     * @param partIndex 取得するパーツのインデックス
     * @return パーツのID
     */
    getPartId(partIndex) {
      const partId = this._model.parts.ids[partIndex];
      return CubismFramework.getIdManager().getId(partId);
    }
    /**
     * パーツの個数の取得
     * @return パーツの個数
     */
    getPartCount() {
      const partCount = this._model.parts.count;
      return partCount;
    }
    /**
     * パーツの不透明度の設定(Index)
     * @param partIndex パーツのインデックス
     * @param opacity 不透明度
     */
    setPartOpacityByIndex(partIndex, opacity) {
      if (this._notExistPartOpacities.isExist(partIndex)) {
        this._notExistPartOpacities.setValue(partIndex, opacity);
        return;
      }
      CSM_ASSERT(0 <= partIndex && partIndex < this.getPartCount());
      this._partOpacities[partIndex] = opacity;
    }
    /**
     * パーツの不透明度の設定(Id)
     * @param partId パーツのID
     * @param opacity パーツの不透明度
     */
    setPartOpacityById(partId, opacity) {
      const index = this.getPartIndex(partId);
      if (index < 0) {
        return;
      }
      this.setPartOpacityByIndex(index, opacity);
    }
    /**
     * パーツの不透明度の取得(index)
     * @param partIndex パーツのインデックス
     * @return パーツの不透明度
     */
    getPartOpacityByIndex(partIndex) {
      if (this._notExistPartOpacities.isExist(partIndex)) {
        return this._notExistPartOpacities.getValue(partIndex);
      }
      CSM_ASSERT(0 <= partIndex && partIndex < this.getPartCount());
      return this._partOpacities[partIndex];
    }
    /**
     * パーツの不透明度の取得(id)
     * @param partId パーツのＩｄ
     * @return パーツの不透明度
     */
    getPartOpacityById(partId) {
      const index = this.getPartIndex(partId);
      if (index < 0) {
        return 0;
      }
      return this.getPartOpacityByIndex(index);
    }
    /**
     * パラメータのインデックスの取得
     * @param パラメータID
     * @return パラメータのインデックス
     */
    getParameterIndex(parameterId) {
      let parameterIndex;
      const idCount = this._model.parameters.count;
      for (parameterIndex = 0; parameterIndex < idCount; ++parameterIndex) {
        if (parameterId != this._parameterIds.at(parameterIndex)) {
          continue;
        }
        return parameterIndex;
      }
      if (this._notExistParameterId.isExist(parameterId)) {
        return this._notExistParameterId.getValue(parameterId);
      }
      parameterIndex = this._model.parameters.count + this._notExistParameterId.getSize();
      this._notExistParameterId.setValue(parameterId, parameterIndex);
      this._notExistParameterValues.appendKey(parameterIndex);
      return parameterIndex;
    }
    /**
     * パラメータの個数の取得
     * @return パラメータの個数
     */
    getParameterCount() {
      return this._model.parameters.count;
    }
    /**
     * パラメータの種類の取得
     * @param parameterIndex パラメータのインデックス
     * @return csmParameterType_Normal -> 通常のパラメータ
     *          csmParameterType_BlendShape -> ブレンドシェイプパラメータ
     */
    getParameterType(parameterIndex) {
      return this._model.parameters.types[parameterIndex];
    }
    /**
     * パラメータの最大値の取得
     * @param parameterIndex パラメータのインデックス
     * @return パラメータの最大値
     */
    getParameterMaximumValue(parameterIndex) {
      return this._model.parameters.maximumValues[parameterIndex];
    }
    /**
     * パラメータの最小値の取得
     * @param parameterIndex パラメータのインデックス
     * @return パラメータの最小値
     */
    getParameterMinimumValue(parameterIndex) {
      return this._model.parameters.minimumValues[parameterIndex];
    }
    /**
     * パラメータのデフォルト値の取得
     * @param parameterIndex パラメータのインデックス
     * @return パラメータのデフォルト値
     */
    getParameterDefaultValue(parameterIndex) {
      return this._model.parameters.defaultValues[parameterIndex];
    }
    /**
     * 指定したパラメータindexのIDを取得
     *
     * @param parameterIndex パラメータのインデックス
     * @returns パラメータID
     */
    getParameterId(parameterIndex) {
      return CubismFramework.getIdManager().getId(
        this._model.parameters.ids[parameterIndex]
      );
    }
    /**
     * パラメータの値の取得
     * @param parameterIndex    パラメータのインデックス
     * @return パラメータの値
     */
    getParameterValueByIndex(parameterIndex) {
      if (this._notExistParameterValues.isExist(parameterIndex)) {
        return this._notExistParameterValues.getValue(parameterIndex);
      }
      CSM_ASSERT(
        0 <= parameterIndex && parameterIndex < this.getParameterCount()
      );
      return this._parameterValues[parameterIndex];
    }
    /**
     * パラメータの値の取得
     * @param parameterId    パラメータのID
     * @return パラメータの値
     */
    getParameterValueById(parameterId) {
      const parameterIndex = this.getParameterIndex(parameterId);
      return this.getParameterValueByIndex(parameterIndex);
    }
    /**
     * パラメータの値の設定
     * @param parameterIndex パラメータのインデックス
     * @param value パラメータの値
     * @param weight 重み
     */
    setParameterValueByIndex(parameterIndex, value, weight = 1) {
      if (this._notExistParameterValues.isExist(parameterIndex)) {
        this._notExistParameterValues.setValue(
          parameterIndex,
          weight == 1 ? value : this._notExistParameterValues.getValue(parameterIndex) * (1 - weight) + value * weight
        );
        return;
      }
      CSM_ASSERT(
        0 <= parameterIndex && parameterIndex < this.getParameterCount()
      );
      if (this._model.parameters.maximumValues[parameterIndex] < value) {
        value = this._model.parameters.maximumValues[parameterIndex];
      }
      if (this._model.parameters.minimumValues[parameterIndex] > value) {
        value = this._model.parameters.minimumValues[parameterIndex];
      }
      this._parameterValues[parameterIndex] = weight == 1 ? value : this._parameterValues[parameterIndex] = this._parameterValues[parameterIndex] * (1 - weight) + value * weight;
    }
    /**
     * パラメータの値の設定
     * @param parameterId パラメータのID
     * @param value パラメータの値
     * @param weight 重み
     */
    setParameterValueById(parameterId, value, weight = 1) {
      const index = this.getParameterIndex(parameterId);
      this.setParameterValueByIndex(index, value, weight);
    }
    /**
     * パラメータの値の加算(index)
     * @param parameterIndex パラメータインデックス
     * @param value 加算する値
     * @param weight 重み
     */
    addParameterValueByIndex(parameterIndex, value, weight = 1) {
      this.setParameterValueByIndex(
        parameterIndex,
        this.getParameterValueByIndex(parameterIndex) + value * weight
      );
    }
    /**
     * パラメータの値の加算(id)
     * @param parameterId パラメータＩＤ
     * @param value 加算する値
     * @param weight 重み
     */
    addParameterValueById(parameterId, value, weight = 1) {
      const index = this.getParameterIndex(parameterId);
      this.addParameterValueByIndex(index, value, weight);
    }
    /**
     * パラメータの値の乗算
     * @param parameterId パラメータのID
     * @param value 乗算する値
     * @param weight 重み
     */
    multiplyParameterValueById(parameterId, value, weight = 1) {
      const index = this.getParameterIndex(parameterId);
      this.multiplyParameterValueByIndex(index, value, weight);
    }
    /**
     * パラメータの値の乗算
     * @param parameterIndex パラメータのインデックス
     * @param value 乗算する値
     * @param weight 重み
     */
    multiplyParameterValueByIndex(parameterIndex, value, weight = 1) {
      this.setParameterValueByIndex(
        parameterIndex,
        this.getParameterValueByIndex(parameterIndex) * (1 + (value - 1) * weight)
      );
    }
    /**
     * Drawableのインデックスの取得
     * @param drawableId DrawableのID
     * @return Drawableのインデックス
     */
    getDrawableIndex(drawableId) {
      const drawableCount = this._model.drawables.count;
      for (let drawableIndex = 0; drawableIndex < drawableCount; ++drawableIndex) {
        if (this._drawableIds.at(drawableIndex) == drawableId) {
          return drawableIndex;
        }
      }
      return -1;
    }
    /**
     * Drawableの個数の取得
     * @return drawableの個数
     */
    getDrawableCount() {
      const drawableCount = this._model.drawables.count;
      return drawableCount;
    }
    /**
     * DrawableのIDを取得する
     * @param drawableIndex Drawableのインデックス
     * @return drawableのID
     */
    getDrawableId(drawableIndex) {
      const parameterIds = this._model.drawables.ids;
      return CubismFramework.getIdManager().getId(parameterIds[drawableIndex]);
    }
    /**
     * Drawableの描画順リストの取得
     * @return Drawableの描画順リスト
     */
    getDrawableRenderOrders() {
      const renderOrders = this._model.drawables.renderOrders;
      return renderOrders;
    }
    /**
     * @deprecated
     * 関数名が誤っていたため、代替となる getDrawableTextureIndex を追加し、この関数は非推奨となりました。
     *
     * Drawableのテクスチャインデックスリストの取得
     * @param drawableIndex Drawableのインデックス
     * @return drawableのテクスチャインデックスリスト
     */
    getDrawableTextureIndices(drawableIndex) {
      return this.getDrawableTextureIndex(drawableIndex);
    }
    /**
     * Drawableのテクスチャインデックスの取得
     * @param drawableIndex Drawableのインデックス
     * @return drawableのテクスチャインデックス
     */
    getDrawableTextureIndex(drawableIndex) {
      const textureIndices = this._model.drawables.textureIndices;
      return textureIndices[drawableIndex];
    }
    /**
     * DrawableのVertexPositionsの変化情報の取得
     *
     * 直近のCubismModel.update関数でDrawableの頂点情報が変化したかを取得する。
     *
     * @param   drawableIndex   Drawableのインデックス
     * @retval  true    Drawableの頂点情報が直近のCubismModel.update関数で変化した
     * @retval  false   Drawableの頂点情報が直近のCubismModel.update関数で変化していない
     */
    getDrawableDynamicFlagVertexPositionsDidChange(drawableIndex) {
      const dynamicFlags = this._model.drawables.dynamicFlags;
      return Live2DCubismCore.Utils.hasVertexPositionsDidChangeBit(
        dynamicFlags[drawableIndex]
      );
    }
    /**
     * Drawableの頂点インデックスの個数の取得
     * @param drawableIndex Drawableのインデックス
     * @return drawableの頂点インデックスの個数
     */
    getDrawableVertexIndexCount(drawableIndex) {
      const indexCounts = this._model.drawables.indexCounts;
      return indexCounts[drawableIndex];
    }
    /**
     * Drawableの頂点の個数の取得
     * @param drawableIndex Drawableのインデックス
     * @return drawableの頂点の個数
     */
    getDrawableVertexCount(drawableIndex) {
      const vertexCounts = this._model.drawables.vertexCounts;
      return vertexCounts[drawableIndex];
    }
    /**
     * Drawableの頂点リストの取得
     * @param drawableIndex drawableのインデックス
     * @return drawableの頂点リスト
     */
    getDrawableVertices(drawableIndex) {
      return this.getDrawableVertexPositions(drawableIndex);
    }
    /**
     * Drawableの頂点インデックスリストの取得
     * @param drawableIndex Drawableのインデックス
     * @return drawableの頂点インデックスリスト
     */
    getDrawableVertexIndices(drawableIndex) {
      const indicesArray = this._model.drawables.indices;
      return indicesArray[drawableIndex];
    }
    /**
     * Drawableの頂点リストの取得
     * @param drawableIndex Drawableのインデックス
     * @return drawableの頂点リスト
     */
    getDrawableVertexPositions(drawableIndex) {
      const verticesArray = this._model.drawables.vertexPositions;
      return verticesArray[drawableIndex];
    }
    /**
     * Drawableの頂点のUVリストの取得
     * @param drawableIndex Drawableのインデックス
     * @return drawableの頂点UVリスト
     */
    getDrawableVertexUvs(drawableIndex) {
      const uvsArray = this._model.drawables.vertexUvs;
      return uvsArray[drawableIndex];
    }
    /**
     * Drawableの不透明度の取得
     * @param drawableIndex Drawableのインデックス
     * @return drawableの不透明度
     */
    getDrawableOpacity(drawableIndex) {
      const opacities = this._model.drawables.opacities;
      return opacities[drawableIndex];
    }
    /**
     * Drawableの乗算色の取得
     * @param drawableIndex Drawableのインデックス
     * @return drawableの乗算色(RGBA)
     * スクリーン色はRGBAで取得されるが、Aは必ず0
     */
    getDrawableMultiplyColor(drawableIndex) {
      const multiplyColors = this._model.drawables.multiplyColors;
      const index = drawableIndex * 4;
      const multiplyColor = new CubismTextureColor();
      multiplyColor.r = multiplyColors[index];
      multiplyColor.g = multiplyColors[index + 1];
      multiplyColor.b = multiplyColors[index + 2];
      multiplyColor.a = multiplyColors[index + 3];
      return multiplyColor;
    }
    /**
     * Drawableのスクリーン色の取得
     * @param drawableIndex Drawableのインデックス
     * @return drawableのスクリーン色(RGBA)
     * スクリーン色はRGBAで取得されるが、Aは必ず0
     */
    getDrawableScreenColor(drawableIndex) {
      const screenColors = this._model.drawables.screenColors;
      const index = drawableIndex * 4;
      const screenColor = new CubismTextureColor();
      screenColor.r = screenColors[index];
      screenColor.g = screenColors[index + 1];
      screenColor.b = screenColors[index + 2];
      screenColor.a = screenColors[index + 3];
      return screenColor;
    }
    /**
     * Drawableの親パーツのインデックスの取得
     * @param drawableIndex Drawableのインデックス
     * @return drawableの親パーツのインデックス
     */
    getDrawableParentPartIndex(drawableIndex) {
      return this._model.drawables.parentPartIndices[drawableIndex];
    }
    /**
     * Drawableのブレンドモードを取得
     * @param drawableIndex Drawableのインデックス
     * @return drawableのブレンドモード
     */
    getDrawableBlendMode(drawableIndex) {
      const constantFlags = this._model.drawables.constantFlags;
      return Live2DCubismCore.Utils.hasBlendAdditiveBit(
        constantFlags[drawableIndex]
      ) ? 1 /* CubismBlendMode_Additive */ : Live2DCubismCore.Utils.hasBlendMultiplicativeBit(
        constantFlags[drawableIndex]
      ) ? 2 /* CubismBlendMode_Multiplicative */ : 0 /* CubismBlendMode_Normal */;
    }
    /**
     * Drawableのマスクの反転使用の取得
     *
     * Drawableのマスク使用時の反転設定を取得する。
     * マスクを使用しない場合は無視される。
     *
     * @param drawableIndex Drawableのインデックス
     * @return Drawableの反転設定
     */
    getDrawableInvertedMaskBit(drawableIndex) {
      const constantFlags = this._model.drawables.constantFlags;
      return Live2DCubismCore.Utils.hasIsInvertedMaskBit(
        constantFlags[drawableIndex]
      );
    }
    /**
     * Drawableのクリッピングマスクリストの取得
     * @return Drawableのクリッピングマスクリスト
     */
    getDrawableMasks() {
      const masks = this._model.drawables.masks;
      return masks;
    }
    /**
     * Drawableのクリッピングマスクの個数リストの取得
     * @return Drawableのクリッピングマスクの個数リスト
     */
    getDrawableMaskCounts() {
      const maskCounts = this._model.drawables.maskCounts;
      return maskCounts;
    }
    /**
     * クリッピングマスクの使用状態
     *
     * @return true クリッピングマスクを使用している
     * @return false クリッピングマスクを使用していない
     */
    isUsingMasking() {
      for (let d = 0; d < this._model.drawables.count; ++d) {
        if (this._model.drawables.maskCounts[d] <= 0) {
          continue;
        }
        return true;
      }
      return false;
    }
    /**
     * Drawableの表示情報を取得する
     *
     * @param drawableIndex Drawableのインデックス
     * @return true Drawableが表示
     * @return false Drawableが非表示
     */
    getDrawableDynamicFlagIsVisible(drawableIndex) {
      const dynamicFlags = this._model.drawables.dynamicFlags;
      return Live2DCubismCore.Utils.hasIsVisibleBit(dynamicFlags[drawableIndex]);
    }
    /**
     * DrawableのDrawOrderの変化情報の取得
     *
     * 直近のCubismModel.update関数でdrawableのdrawOrderが変化したかを取得する。
     * drawOrderはartMesh上で指定する0から1000の情報
     * @param drawableIndex drawableのインデックス
     * @return true drawableの不透明度が直近のCubismModel.update関数で変化した
     * @return false drawableの不透明度が直近のCubismModel.update関数で変化している
     */
    getDrawableDynamicFlagVisibilityDidChange(drawableIndex) {
      const dynamicFlags = this._model.drawables.dynamicFlags;
      return Live2DCubismCore.Utils.hasVisibilityDidChangeBit(
        dynamicFlags[drawableIndex]
      );
    }
    /**
     * Drawableの不透明度の変化情報の取得
     *
     * 直近のCubismModel.update関数でdrawableの不透明度が変化したかを取得する。
     *
     * @param drawableIndex drawableのインデックス
     * @return true Drawableの不透明度が直近のCubismModel.update関数で変化した
     * @return false Drawableの不透明度が直近のCubismModel.update関数で変化してない
     */
    getDrawableDynamicFlagOpacityDidChange(drawableIndex) {
      const dynamicFlags = this._model.drawables.dynamicFlags;
      return Live2DCubismCore.Utils.hasOpacityDidChangeBit(
        dynamicFlags[drawableIndex]
      );
    }
    /**
     * Drawableの描画順序の変化情報の取得
     *
     * 直近のCubismModel.update関数でDrawableの描画の順序が変化したかを取得する。
     *
     * @param drawableIndex Drawableのインデックス
     * @return true Drawableの描画の順序が直近のCubismModel.update関数で変化した
     * @return false Drawableの描画の順序が直近のCubismModel.update関数で変化してない
     */
    getDrawableDynamicFlagRenderOrderDidChange(drawableIndex) {
      const dynamicFlags = this._model.drawables.dynamicFlags;
      return Live2DCubismCore.Utils.hasRenderOrderDidChangeBit(
        dynamicFlags[drawableIndex]
      );
    }
    /**
     * Drawableの乗算色・スクリーン色の変化情報の取得
     *
     * 直近のCubismModel.update関数でDrawableの乗算色・スクリーン色が変化したかを取得する。
     *
     * @param drawableIndex Drawableのインデックス
     * @return true Drawableの乗算色・スクリーン色が直近のCubismModel.update関数で変化した
     * @return false Drawableの乗算色・スクリーン色が直近のCubismModel.update関数で変化してない
     */
    getDrawableDynamicFlagBlendColorDidChange(drawableIndex) {
      const dynamicFlags = this._model.drawables.dynamicFlags;
      return Live2DCubismCore.Utils.hasBlendColorDidChangeBit(
        dynamicFlags[drawableIndex]
      );
    }
    /**
     * 保存されたパラメータの読み込み
     */
    loadParameters() {
      let parameterCount = this._model.parameters.count;
      const savedParameterCount = this._savedParameters.getSize();
      if (parameterCount > savedParameterCount) {
        parameterCount = savedParameterCount;
      }
      for (let i = 0; i < parameterCount; ++i) {
        this._parameterValues[i] = this._savedParameters.at(i);
      }
    }
    /**
     * 初期化する
     */
    initialize() {
      CSM_ASSERT(this._model);
      this._parameterValues = this._model.parameters.values;
      this._partOpacities = this._model.parts.opacities;
      this._parameterMaximumValues = this._model.parameters.maximumValues;
      this._parameterMinimumValues = this._model.parameters.minimumValues;
      {
        const parameterIds = this._model.parameters.ids;
        const parameterCount = this._model.parameters.count;
        this._parameterIds.prepareCapacity(parameterCount);
        for (let i = 0; i < parameterCount; ++i) {
          this._parameterIds.pushBack(
            CubismFramework.getIdManager().getId(parameterIds[i])
          );
        }
      }
      const partCount = this._model.parts.count;
      {
        const partIds = this._model.parts.ids;
        this._partIds.prepareCapacity(partCount);
        for (let i = 0; i < partCount; ++i) {
          this._partIds.pushBack(
            CubismFramework.getIdManager().getId(partIds[i])
          );
        }
        this._userPartMultiplyColors.prepareCapacity(partCount);
        this._userPartScreenColors.prepareCapacity(partCount);
        this._partChildDrawables.prepareCapacity(partCount);
      }
      {
        const drawableIds = this._model.drawables.ids;
        const drawableCount = this._model.drawables.count;
        this._userMultiplyColors.prepareCapacity(drawableCount);
        this._userScreenColors.prepareCapacity(drawableCount);
        this._userCullings.prepareCapacity(drawableCount);
        const userCulling = new DrawableCullingData(
          false,
          false
        );
        {
          for (let i = 0; i < partCount; ++i) {
            const multiplyColor = new CubismTextureColor(
              1,
              1,
              1,
              1
            );
            const screenColor = new CubismTextureColor(
              0,
              0,
              0,
              1
            );
            const userMultiplyColor = new PartColorData(
              false,
              multiplyColor
            );
            const userScreenColor = new PartColorData(
              false,
              screenColor
            );
            this._userPartMultiplyColors.pushBack(userMultiplyColor);
            this._userPartScreenColors.pushBack(userScreenColor);
            this._partChildDrawables.pushBack(new csmVector());
            this._partChildDrawables.at(i).prepareCapacity(drawableCount);
          }
        }
        {
          for (let i = 0; i < drawableCount; ++i) {
            const multiplyColor = new CubismTextureColor(
              1,
              1,
              1,
              1
            );
            const screenColor = new CubismTextureColor(
              0,
              0,
              0,
              1
            );
            const userMultiplyColor = new DrawableColorData(
              false,
              multiplyColor
            );
            const userScreenColor = new DrawableColorData(
              false,
              screenColor
            );
            this._drawableIds.pushBack(
              CubismFramework.getIdManager().getId(drawableIds[i])
            );
            this._userMultiplyColors.pushBack(userMultiplyColor);
            this._userScreenColors.pushBack(userScreenColor);
            this._userCullings.pushBack(userCulling);
            const parentIndex = this.getDrawableParentPartIndex(i);
            if (parentIndex >= 0) {
              this._partChildDrawables.at(parentIndex).pushBack(i);
            }
          }
        }
      }
    }
    /**
     * デストラクタ相当の処理
     */
    release() {
      this._model.release();
      this._model = null;
    }
    // カリング設定の配列
  };
  var Live2DCubismFramework36;
  ((Live2DCubismFramework42) => {
    Live2DCubismFramework42.CubismModel = CubismModel;
  })(Live2DCubismFramework36 || (Live2DCubismFramework36 = {}));

  // .trellis/workspace/lapp-runtime-src/src/renderer/WebSDK/Framework/src/model/cubismmoc.ts
  var CubismMoc = class _CubismMoc {
    /**
     * コンストラクタ
     */
    constructor(moc) {
      __publicField(this, "_moc");
      // Mocデータ
      __publicField(this, "_modelCount");
      // Mocデータから作られたモデルの個数
      __publicField(this, "_mocVersion");
      this._moc = moc;
      this._modelCount = 0;
      this._mocVersion = 0;
    }
    /**
     * Mocデータの作成
     */
    static create(mocBytes, shouldCheckMocConsistency) {
      let cubismMoc = null;
      if (shouldCheckMocConsistency) {
        const consistency = this.hasMocConsistency(mocBytes);
        if (!consistency) {
          CubismLogError(`Inconsistent MOC3.`);
          return cubismMoc;
        }
      }
      const moc = Live2DCubismCore.Moc.fromArrayBuffer(mocBytes);
      if (moc) {
        cubismMoc = new _CubismMoc(moc);
        cubismMoc._mocVersion = Live2DCubismCore.Version.csmGetMocVersion(
          moc,
          mocBytes
        );
      }
      return cubismMoc;
    }
    /**
     * Mocデータを削除
     *
     * Mocデータを削除する
     */
    static delete(moc) {
      moc._moc._release();
      moc._moc = null;
      moc = null;
    }
    /**
     * モデルを作成する
     *
     * @return Mocデータから作成されたモデル
     */
    createModel() {
      let cubismModel = null;
      const model = Live2DCubismCore.Model.fromMoc(
        this._moc
      );
      if (model) {
        cubismModel = new CubismModel(model);
        cubismModel.initialize();
        ++this._modelCount;
      }
      return cubismModel;
    }
    /**
     * モデルを削除する
     */
    deleteModel(model) {
      if (model != null) {
        model.release();
        model = null;
        --this._modelCount;
      }
    }
    /**
     * デストラクタ相当の処理
     */
    release() {
      CSM_ASSERT(this._modelCount == 0);
      this._moc._release();
      this._moc = null;
    }
    /**
     * 最新の.moc3 Versionを取得
     */
    getLatestMocVersion() {
      return Live2DCubismCore.Version.csmGetLatestMocVersion();
    }
    /**
     * 読み込んだモデルの.moc3 Versionを取得
     */
    getMocVersion() {
      return this._mocVersion;
    }
    /**
     * .moc3 の整合性を検証する
     */
    static hasMocConsistency(mocBytes) {
      const isConsistent = Live2DCubismCore.Moc.prototype.hasMocConsistency(mocBytes);
      return isConsistent === 1 ? true : false;
    }
    // 読み込んだモデルの.moc3 Version
  };
  var Live2DCubismFramework37;
  ((Live2DCubismFramework42) => {
    Live2DCubismFramework42.CubismMoc = CubismMoc;
  })(Live2DCubismFramework37 || (Live2DCubismFramework37 = {}));

  // .trellis/workspace/lapp-runtime-src/src/renderer/WebSDK/Framework/src/model/cubismmodeluserdatajson.ts
  var Meta3 = "Meta";
  var UserDataCount2 = "UserDataCount";
  var TotalUserDataSize2 = "TotalUserDataSize";
  var UserData3 = "UserData";
  var Target2 = "Target";
  var Id5 = "Id";
  var Value7 = "Value";
  var CubismModelUserDataJson = class {
    /**
     * コンストラクタ
     * @param buffer    userdata3.jsonが読み込まれているバッファ
     * @param size      バッファのサイズ
     */
    constructor(buffer, size) {
      __publicField(this, "_json");
      this._json = CubismJson.create(buffer, size);
    }
    /**
     * デストラクタ相当の処理
     */
    release() {
      CubismJson.delete(this._json);
    }
    /**
     * ユーザーデータ個数の取得
     * @return ユーザーデータの個数
     */
    getUserDataCount() {
      return this._json.getRoot().getValueByString(Meta3).getValueByString(UserDataCount2).toInt();
    }
    /**
     * ユーザーデータ総文字列数の取得
     *
     * @return ユーザーデータ総文字列数
     */
    getTotalUserDataSize() {
      return this._json.getRoot().getValueByString(Meta3).getValueByString(TotalUserDataSize2).toInt();
    }
    /**
     * ユーザーデータのタイプの取得
     *
     * @return ユーザーデータのタイプ
     */
    getUserDataTargetType(i) {
      return this._json.getRoot().getValueByString(UserData3).getValueByIndex(i).getValueByString(Target2).getRawString();
    }
    /**
     * ユーザーデータのターゲットIDの取得
     *
     * @param i インデックス
     * @return ユーザーデータターゲットID
     */
    getUserDataId(i) {
      return CubismFramework.getIdManager().getId(
        this._json.getRoot().getValueByString(UserData3).getValueByIndex(i).getValueByString(Id5).getRawString()
      );
    }
    /**
     * ユーザーデータの文字列の取得
     *
     * @param i インデックス
     * @return ユーザーデータ
     */
    getUserDataValue(i) {
      return this._json.getRoot().getValueByString(UserData3).getValueByIndex(i).getValueByString(Value7).getRawString();
    }
  };
  var Live2DCubismFramework38;
  ((Live2DCubismFramework42) => {
    Live2DCubismFramework42.CubismModelUserDataJson = CubismModelUserDataJson;
  })(Live2DCubismFramework38 || (Live2DCubismFramework38 = {}));

  // .trellis/workspace/lapp-runtime-src/src/renderer/WebSDK/Framework/src/model/cubismmodeluserdata.ts
  var ArtMesh = "ArtMesh";
  var CubismModelUserDataNode = class {
    constructor() {
      __publicField(this, "targetType");
      // ユーザーデータターゲットタイプ
      __publicField(this, "targetId");
      // ユーザーデータターゲットのID
      __publicField(this, "value");
    }
    // ユーザーデータ
  };
  var CubismModelUserData = class _CubismModelUserData {
    /**
     * コンストラクタ
     */
    constructor() {
      __publicField(this, "_userDataNodes");
      // ユーザーデータ構造体配列
      __publicField(this, "_artMeshUserDataNode");
      this._userDataNodes = new csmVector();
      this._artMeshUserDataNode = new csmVector();
    }
    /**
     * インスタンスの作成
     *
     * @param buffer    userdata3.jsonが読み込まれているバッファ
     * @param size      バッファのサイズ
     * @return 作成されたインスタンス
     */
    static create(buffer, size) {
      const ret = new _CubismModelUserData();
      ret.parseUserData(buffer, size);
      return ret;
    }
    /**
     * インスタンスを破棄する
     *
     * @param modelUserData 破棄するインスタンス
     */
    static delete(modelUserData) {
      if (modelUserData != null) {
        modelUserData.release();
        modelUserData = null;
      }
    }
    /**
     * ArtMeshのユーザーデータのリストの取得
     *
     * @return ユーザーデータリスト
     */
    getArtMeshUserDatas() {
      return this._artMeshUserDataNode;
    }
    /**
     * userdata3.jsonのパース
     *
     * @param buffer    userdata3.jsonが読み込まれているバッファ
     * @param size      バッファのサイズ
     */
    parseUserData(buffer, size) {
      let json = new CubismModelUserDataJson(
        buffer,
        size
      );
      if (!json) {
        json.release();
        json = void 0;
        return;
      }
      const typeOfArtMesh = CubismFramework.getIdManager().getId(ArtMesh);
      const nodeCount = json.getUserDataCount();
      for (let i = 0; i < nodeCount; i++) {
        const addNode = new CubismModelUserDataNode();
        addNode.targetId = json.getUserDataId(i);
        addNode.targetType = CubismFramework.getIdManager().getId(
          json.getUserDataTargetType(i)
        );
        addNode.value = new csmString(json.getUserDataValue(i));
        this._userDataNodes.pushBack(addNode);
        if (addNode.targetType == typeOfArtMesh) {
          this._artMeshUserDataNode.pushBack(addNode);
        }
      }
      json.release();
      json = void 0;
    }
    /**
     * デストラクタ相当の処理
     *
     * ユーザーデータ構造体配列を解放する
     */
    release() {
      for (let i = 0; i < this._userDataNodes.getSize(); ++i) {
        this._userDataNodes.set(i, null);
      }
      this._userDataNodes = null;
    }
    // 閲覧リストの保持
  };
  var Live2DCubismFramework39;
  ((Live2DCubismFramework42) => {
    Live2DCubismFramework42.CubismModelUserData = CubismModelUserData;
    Live2DCubismFramework42.CubismModelUserDataNode = CubismModelUserDataNode;
  })(Live2DCubismFramework39 || (Live2DCubismFramework39 = {}));

  // .trellis/workspace/lapp-runtime-src/src/renderer/WebSDK/Framework/src/model/cubismusermodel.ts
  var CubismUserModel = class _CubismUserModel {
    /**
     * コンストラクタ
     */
    constructor() {
      __publicField(this, "_moc");
      // Mocデータ
      __publicField(this, "_model");
      // Modelインスタンス
      __publicField(this, "_motionManager");
      // モーション管理
      __publicField(this, "_expressionManager");
      // 表情管理
      __publicField(this, "_eyeBlink");
      // 自動まばたき
      __publicField(this, "_breath");
      // 呼吸
      __publicField(this, "_modelMatrix");
      // モデル行列
      __publicField(this, "_pose");
      // ポーズ管理
      __publicField(this, "_dragManager");
      // マウスドラッグ
      __publicField(this, "_physics");
      // 物理演算
      __publicField(this, "_modelUserData");
      // ユーザーデータ
      __publicField(this, "_initialized");
      // 初期化されたかどうか
      __publicField(this, "_updating");
      // 更新されたかどうか
      __publicField(this, "_opacity");
      // 不透明度
      __publicField(this, "_lipsync");
      // リップシンクするかどうか
      __publicField(this, "_lastLipSyncValue");
      // 最後のリップシンクの制御地
      __publicField(this, "_dragX");
      // マウスドラッグのX位置
      __publicField(this, "_dragY");
      // マウスドラッグのY位置
      __publicField(this, "_accelerationX");
      // X軸方向の加速度
      __publicField(this, "_accelerationY");
      // Y軸方向の加速度
      __publicField(this, "_accelerationZ");
      // Z軸方向の加速度
      __publicField(this, "_mocConsistency");
      // MOC3一貫性検証するかどうか
      __publicField(this, "_debugMode");
      // デバッグモードかどうか
      __publicField(this, "_renderer");
      this._moc = null;
      this._model = null;
      this._motionManager = null;
      this._expressionManager = null;
      this._eyeBlink = null;
      this._breath = null;
      this._modelMatrix = null;
      this._pose = null;
      this._dragManager = null;
      this._physics = null;
      this._modelUserData = null;
      this._initialized = false;
      this._updating = false;
      this._opacity = 1;
      this._lipsync = true;
      this._lastLipSyncValue = 0;
      this._dragX = 0;
      this._dragY = 0;
      this._accelerationX = 0;
      this._accelerationY = 0;
      this._accelerationZ = 0;
      this._mocConsistency = false;
      this._debugMode = false;
      this._renderer = null;
      this._motionManager = new CubismMotionManager();
      this._motionManager.setEventCallback(
        _CubismUserModel.cubismDefaultMotionEventCallback,
        this
      );
      this._expressionManager = new CubismExpressionMotionManager();
      this._dragManager = new CubismTargetPoint();
    }
    /**
     * 初期化状態の取得
     *
     * 初期化されている状態か？
     *
     * @return true     初期化されている
     * @return false    初期化されていない
     */
    isInitialized() {
      return this._initialized;
    }
    /**
     * 初期化状態の設定
     *
     * 初期化状態を設定する。
     *
     * @param v 初期化状態
     */
    setInitialized(v) {
      this._initialized = v;
    }
    /**
     * 更新状態の取得
     *
     * 更新されている状態か？
     *
     * @return true     更新されている
     * @return false    更新されていない
     */
    isUpdating() {
      return this._updating;
    }
    /**
     * 更新状態の設定
     *
     * 更新状態を設定する
     *
     * @param v 更新状態
     */
    setUpdating(v) {
      this._updating = v;
    }
    /**
     * マウスドラッグ情報の設定
     * @param ドラッグしているカーソルのX位置
     * @param ドラッグしているカーソルのY位置
     */
    setDragging(x, y) {
      this._dragManager.set(x, y);
    }
    /**
     * 加速度の情報を設定する
     * @param x X軸方向の加速度
     * @param y Y軸方向の加速度
     * @param z Z軸方向の加速度
     */
    setAcceleration(x, y, z) {
      this._accelerationX = x;
      this._accelerationY = y;
      this._accelerationZ = z;
    }
    /**
     * モデル行列を取得する
     * @return モデル行列
     */
    getModelMatrix() {
      return this._modelMatrix;
    }
    /**
     * 不透明度の設定
     * @param a 不透明度
     */
    setOpacity(a) {
      this._opacity = a;
    }
    /**
     * 不透明度の取得
     * @return 不透明度
     */
    getOpacity() {
      return this._opacity;
    }
    /**
     * モデルデータを読み込む
     *
     * @param buffer    moc3ファイルが読み込まれているバッファ
     */
    loadModel(buffer, shouldCheckMocConsistency = false, kScale = 1) {
      this._moc = CubismMoc.create(buffer, shouldCheckMocConsistency);
      if (this._moc == null) {
        CubismLogError("Failed to CubismMoc.create().");
        return;
      }
      this._model = this._moc.createModel();
      if (this._model == null) {
        CubismLogError("Failed to CreateModel().");
        return;
      }
      this._model.saveParameters();
      this._modelMatrix = new CubismModelMatrix(
        this._model.getCanvasWidth(),
        this._model.getCanvasHeight()
      );
      this._modelMatrix.scale(kScale, kScale);
    }
    /**
     * モーションデータを読み込む
     * @param buffer motion3.jsonファイルが読み込まれているバッファ
     * @param size バッファのサイズ
     * @param name モーションの名前
     * @param onFinishedMotionHandler モーション再生終了時に呼び出されるコールバック関数
     * @return モーションクラス
     */
    loadMotion(buffer, size, name, onFinishedMotionHandler) {
      if (buffer == null || size == 0) {
        CubismLogError("Failed to loadMotion().");
        return null;
      }
      return CubismMotion.create(buffer, size, onFinishedMotionHandler);
    }
    /**
     * 表情データの読み込み
     * @param buffer expファイルが読み込まれているバッファ
     * @param size バッファのサイズ
     * @param name 表情の名前
     */
    loadExpression(buffer, size, name) {
      if (buffer == null || size == 0) {
        CubismLogError("Failed to loadExpression().");
        return null;
      }
      return CubismExpressionMotion.create(buffer, size);
    }
    /**
     * ポーズデータの読み込み
     * @param buffer pose3.jsonが読み込まれているバッファ
     * @param size バッファのサイズ
     */
    loadPose(buffer, size) {
      if (buffer == null || size == 0) {
        CubismLogError("Failed to loadPose().");
        return;
      }
      this._pose = CubismPose.create(buffer, size);
    }
    /**
     * モデルに付属するユーザーデータを読み込む
     * @param buffer userdata3.jsonが読み込まれているバッファ
     * @param size バッファのサイズ
     */
    loadUserData(buffer, size) {
      if (buffer == null || size == 0) {
        CubismLogError("Failed to loadUserData().");
        return;
      }
      this._modelUserData = CubismModelUserData.create(buffer, size);
    }
    /**
     * 物理演算データの読み込み
     * @param buffer  physics3.jsonが読み込まれているバッファ
     * @param size    バッファのサイズ
     */
    loadPhysics(buffer, size) {
      if (buffer == null || size == 0) {
        CubismLogError("Failed to loadPhysics().");
        return;
      }
      this._physics = CubismPhysics.create(buffer, size);
    }
    /**
     * 当たり判定の取得
     * @param drawableId 検証したいDrawableのID
     * @param pointX X位置
     * @param pointY Y位置
     * @return true ヒットしている
     * @return false ヒットしていない
     */
    isHit(drawableId, pointX, pointY) {
      const drawIndex = this._model.getDrawableIndex(drawableId);
      if (drawIndex < 0) {
        return false;
      }
      const count = this._model.getDrawableVertexCount(drawIndex);
      const vertices = this._model.getDrawableVertices(drawIndex);
      let left = vertices[0];
      let right = vertices[0];
      let top = vertices[1];
      let bottom = vertices[1];
      for (let j = 1; j < count; ++j) {
        const x = vertices[Constant.vertexOffset + j * Constant.vertexStep];
        const y = vertices[Constant.vertexOffset + j * Constant.vertexStep + 1];
        if (x < left) {
          left = x;
        }
        if (x > right) {
          right = x;
        }
        if (y < top) {
          top = y;
        }
        if (y > bottom) {
          bottom = y;
        }
      }
      const tx = this._modelMatrix.invertTransformX(pointX);
      const ty = this._modelMatrix.invertTransformY(pointY);
      return left <= tx && tx <= right && top <= ty && ty <= bottom;
    }
    /**
     * モデルの取得
     * @return モデル
     */
    getModel() {
      return this._model;
    }
    /**
     * レンダラの取得
     * @return レンダラ
     */
    getRenderer() {
      return this._renderer;
    }
    /**
     * レンダラを作成して初期化を実行する
     * @param maskBufferCount バッファの生成数
     */
    createRenderer(maskBufferCount = 1) {
      if (this._renderer) {
        this.deleteRenderer();
      }
      this._renderer = new CubismRenderer_WebGL();
      this._renderer.initialize(this._model, maskBufferCount);
    }
    /**
     * レンダラの解放
     */
    deleteRenderer() {
      if (this._renderer != null) {
        this._renderer.release();
        this._renderer = null;
      }
    }
    /**
     * イベント発火時の標準処理
     *
     * Eventが再生処理時にあった場合の処理をする。
     * 継承で上書きすることを想定している。
     * 上書きしない場合はログ出力をする。
     *
     * @param eventValue 発火したイベントの文字列データ
     */
    motionEventFired(eventValue) {
      CubismLogInfo("{0}", eventValue.s);
    }
    /**
     * イベント用のコールバック
     *
     * CubismMotionQueueManagerにイベント用に登録するためのCallback。
     * CubismUserModelの継承先のEventFiredを呼ぶ。
     *
     * @param caller 発火したイベントを管理していたモーションマネージャー、比較用
     * @param eventValue 発火したイベントの文字列データ
     * @param customData CubismUserModelを継承したインスタンスを想定
     */
    static cubismDefaultMotionEventCallback(caller, eventValue, customData) {
      const model = customData;
      if (model != null) {
        model.motionEventFired(eventValue);
      }
    }
    /**
     * デストラクタに相当する処理
     */
    release() {
      if (this._motionManager != null) {
        this._motionManager.release();
        this._motionManager = null;
      }
      if (this._expressionManager != null) {
        this._expressionManager.release();
        this._expressionManager = null;
      }
      if (this._moc != null) {
        this._moc.deleteModel(this._model);
        this._moc.release();
        this._moc = null;
      }
      this._modelMatrix = null;
      CubismPose.delete(this._pose);
      CubismEyeBlink.delete(this._eyeBlink);
      CubismBreath.delete(this._breath);
      this._dragManager = null;
      CubismPhysics.delete(this._physics);
      CubismModelUserData.delete(this._modelUserData);
      this.deleteRenderer();
    }
    // レンダラ
  };
  var Live2DCubismFramework40;
  ((Live2DCubismFramework42) => {
    Live2DCubismFramework42.CubismUserModel = CubismUserModel;
  })(Live2DCubismFramework40 || (Live2DCubismFramework40 = {}));

  // .trellis/workspace/lapp-runtime-src/src/renderer/WebSDK/src/lapppal.ts
  var LAppPal = class {
    /**
     * ファイルをバイトデータとして読みこむ 读取文件为字节数据
     *
     * @param filePath 読み込み対象ファイルのパス [Path to the file to be read]
     * @return
     * {
     *      buffer,   読み込んだバイトデータ [Read byte data]
     *      size        ファイルサイズ [File size]
     * }
     */
    static loadFileAsBytes(filePath, callback) {
      fetch(filePath).then((response) => response.arrayBuffer()).then((arrayBuffer) => callback(arrayBuffer, arrayBuffer.byteLength));
    }
    /**
     * デルタ時間（前回フレームとの差分）を取得する
     * @return デルタ時間[ms]
     * 
     * 获取增量时间（与上一帧的差异）
     */
    static getDeltaTime() {
      return this.s_deltaTime;
    }
    static updateTime(modifyLastFrameTime = true) {
      this.s_currentFrame = Date.now();
      this.s_deltaTime = (this.s_currentFrame - this.s_lastFrame) / 1e3;
      if (modifyLastFrameTime === true) {
        this.s_lastFrame = this.s_currentFrame;
      }
    }
    /**
     * メッセージを出力する
     * @param message 文字列
     * 
     * 输出消息
     */
    static printMessage(message) {
      console.log(message);
    }
  };
  __publicField(LAppPal, "lastUpdate", Date.now());
  __publicField(LAppPal, "s_currentFrame", 0);
  __publicField(LAppPal, "s_lastFrame", 0);
  __publicField(LAppPal, "s_deltaTime", 0);

  // .trellis/workspace/lapp-runtime-src/src/renderer/WebSDK/src/lapptexturemanager.ts
  var LAppTextureManager = class {
    /**
     * コンストラクタ
     */
    constructor() {
      __publicField(this, "_textures");
      this._textures = new csmVector();
    }
    /**
     * 解放する。
     */
    release() {
      for (let ite = this._textures.begin(); ite.notEqual(this._textures.end()); ite.preIncrement()) {
        gl.deleteTexture(ite.ptr().id);
      }
      this._textures = null;
    }
    /**
     * 画像読み込み
     *
     * @param fileName 読み込む画像ファイルパス名
     * @param usePremultiply Premult処理を有効にするか
     * @return 画像情報、読み込み失敗時はnullを返す
     */
    createTextureFromPngFile(fileName, usePremultiply, callback) {
      for (let ite = this._textures.begin(); ite.notEqual(this._textures.end()); ite.preIncrement()) {
        if (ite.ptr().fileName == fileName && ite.ptr().usePremultply == usePremultiply) {
          ite.ptr().img = new Image();
          ite.ptr().img.addEventListener("load", () => callback(ite.ptr()), {
            passive: true
          });
          ite.ptr().img.src = fileName;
          return;
        }
      }
      const img = new Image();
      img.crossOrigin = "anonymous";
      img.addEventListener(
        "load",
        () => {
          const tex = gl.createTexture();
          gl.bindTexture(gl.TEXTURE_2D, tex);
          gl.texParameteri(
            gl.TEXTURE_2D,
            gl.TEXTURE_MIN_FILTER,
            gl.LINEAR_MIPMAP_LINEAR
          );
          gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
          if (usePremultiply) {
            gl.pixelStorei(gl.UNPACK_PREMULTIPLY_ALPHA_WEBGL, 1);
          }
          gl.texImage2D(
            gl.TEXTURE_2D,
            0,
            gl.RGBA,
            gl.RGBA,
            gl.UNSIGNED_BYTE,
            img
          );
          gl.generateMipmap(gl.TEXTURE_2D);
          gl.bindTexture(gl.TEXTURE_2D, null);
          const textureInfo = new TextureInfo();
          if (textureInfo != null) {
            textureInfo.fileName = fileName;
            textureInfo.width = img.width;
            textureInfo.height = img.height;
            textureInfo.id = tex;
            textureInfo.img = img;
            textureInfo.usePremultply = usePremultiply;
            this._textures.pushBack(textureInfo);
          }
          callback(textureInfo);
        },
        { passive: true }
      );
      img.src = fileName;
    }
    /**
     * 画像の解放
     *
     * 配列に存在する画像全てを解放する。
     */
    releaseTextures() {
      for (let i = 0; i < this._textures.getSize(); i++) {
        this._textures.set(i, null);
      }
      this._textures.clear();
    }
    /**
     * 画像の解放
     *
     * 指定したテクスチャの画像を解放する。
     * @param texture 解放するテクスチャ
     */
    releaseTextureByTexture(texture) {
      for (let i = 0; i < this._textures.getSize(); i++) {
        if (this._textures.at(i).id != texture) {
          continue;
        }
        this._textures.set(i, null);
        this._textures.remove(i);
        break;
      }
    }
    /**
     * 画像の解放
     *
     * 指定した名前の画像を解放する。
     * @param fileName 解放する画像ファイルパス名
     */
    releaseTextureByFilePath(fileName) {
      for (let i = 0; i < this._textures.getSize(); i++) {
        if (this._textures.at(i).fileName == fileName) {
          this._textures.set(i, null);
          this._textures.remove(i);
          break;
        }
      }
    }
  };
  var TextureInfo = class {
    constructor() {
      __publicField(this, "img");
      // 画像
      __publicField(this, "id", null);
      // テクスチャ
      __publicField(this, "width", 0);
      // 横幅
      __publicField(this, "height", 0);
      // 高さ
      __publicField(this, "usePremultply");
      // Premult処理を有効にするか
      __publicField(this, "fileName");
    }
    // ファイル名
  };

  // .trellis/workspace/lapp-runtime-src/src/renderer/WebSDK/Framework/src/math/cubismviewmatrix.ts
  var CubismViewMatrix = class extends CubismMatrix44 {
    /**
     * コンストラクタ
     */
    constructor() {
      super();
      __publicField(this, "_screenLeft");
      // デバイスに対応する論理座標上の範囲（左辺X軸位置）
      __publicField(this, "_screenRight");
      // デバイスに対応する論理座標上の範囲（右辺X軸位置）
      __publicField(this, "_screenTop");
      // デバイスに対応する論理座標上の範囲（上辺Y軸位置）
      __publicField(this, "_screenBottom");
      // デバイスに対応する論理座標上の範囲（下辺Y軸位置）
      __publicField(this, "_maxLeft");
      // 論理座標上の移動可能範囲（左辺X軸位置）
      __publicField(this, "_maxRight");
      // 論理座標上の移動可能範囲（右辺X軸位置）
      __publicField(this, "_maxTop");
      // 論理座標上の移動可能範囲（上辺Y軸位置）
      __publicField(this, "_maxBottom");
      // 論理座標上の移動可能範囲（下辺Y軸位置）
      __publicField(this, "_maxScale");
      // 拡大率の最大値
      __publicField(this, "_minScale");
      this._screenLeft = 0;
      this._screenRight = 0;
      this._screenTop = 0;
      this._screenBottom = 0;
      this._maxLeft = 0;
      this._maxRight = 0;
      this._maxTop = 0;
      this._maxBottom = 0;
      this._maxScale = 0;
      this._minScale = 0;
    }
    /**
     * 移動を調整
     *
     * @param x X軸の移動量
     * @param y Y軸の移動量
     */
    adjustTranslate(x, y) {
      if (this._tr[0] * this._maxLeft + (this._tr[12] + x) > this._screenLeft) {
        x = this._screenLeft - this._tr[0] * this._maxLeft - this._tr[12];
      }
      if (this._tr[0] * this._maxRight + (this._tr[12] + x) < this._screenRight) {
        x = this._screenRight - this._tr[0] * this._maxRight - this._tr[12];
      }
      if (this._tr[5] * this._maxTop + (this._tr[13] + y) < this._screenTop) {
        y = this._screenTop - this._tr[5] * this._maxTop - this._tr[13];
      }
      if (this._tr[5] * this._maxBottom + (this._tr[13] + y) > this._screenBottom) {
        y = this._screenBottom - this._tr[5] * this._maxBottom - this._tr[13];
      }
      const tr1 = new Float32Array([
        1,
        0,
        0,
        0,
        0,
        1,
        0,
        0,
        0,
        0,
        1,
        0,
        x,
        y,
        0,
        1
      ]);
      CubismMatrix44.multiply(tr1, this._tr, this._tr);
    }
    /**
     * 拡大率を調整
     *
     * @param cx 拡大を行うX軸の中心位置
     * @param cy 拡大を行うY軸の中心位置
     * @param scale 拡大率
     */
    adjustScale(cx, cy, scale) {
      const maxScale = this.getMaxScale();
      const minScale = this.getMinScale();
      const targetScale = scale * this._tr[0];
      if (targetScale < minScale) {
        if (this._tr[0] > 0) {
          scale = minScale / this._tr[0];
        }
      } else if (targetScale > maxScale) {
        if (this._tr[0] > 0) {
          scale = maxScale / this._tr[0];
        }
      }
      const tr1 = new Float32Array([
        1,
        0,
        0,
        0,
        0,
        1,
        0,
        0,
        0,
        0,
        1,
        0,
        cx,
        cy,
        0,
        1
      ]);
      const tr2 = new Float32Array([
        scale,
        0,
        0,
        0,
        0,
        scale,
        0,
        0,
        0,
        0,
        1,
        0,
        0,
        0,
        0,
        1
      ]);
      const tr3 = new Float32Array([
        1,
        0,
        0,
        0,
        0,
        1,
        0,
        0,
        0,
        0,
        1,
        0,
        -cx,
        -cy,
        0,
        1
      ]);
      CubismMatrix44.multiply(tr3, this._tr, this._tr);
      CubismMatrix44.multiply(tr2, this._tr, this._tr);
      CubismMatrix44.multiply(tr1, this._tr, this._tr);
    }
    /**
     * デバイスに対応する論理座養生の範囲の設定
     *
     * @param left      左辺のX軸の位置
     * @param right     右辺のX軸の位置
     * @param bottom    下辺のY軸の位置
     * @param top       上辺のY軸の位置
     */
    setScreenRect(left, right, bottom, top) {
      this._screenLeft = left;
      this._screenRight = right;
      this._screenBottom = bottom;
      this._screenTop = top;
    }
    /**
     * デバイスに対応する論理座標上の移動可能範囲の設定
     * @param left      左辺のX軸の位置
     * @param right     右辺のX軸の位置
     * @param bottom    下辺のY軸の位置
     * @param top       上辺のY軸の位置
     */
    setMaxScreenRect(left, right, bottom, top) {
      this._maxLeft = left;
      this._maxRight = right;
      this._maxTop = top;
      this._maxBottom = bottom;
    }
    /**
     * 最大拡大率の設定
     * @param maxScale 最大拡大率
     */
    setMaxScale(maxScale) {
      this._maxScale = maxScale;
    }
    /**
     * 最小拡大率の設定
     * @param minScale 最小拡大率
     */
    setMinScale(minScale) {
      this._minScale = minScale;
    }
    /**
     * 最大拡大率の取得
     * @return 最大拡大率
     */
    getMaxScale() {
      return this._maxScale;
    }
    /**
     * 最小拡大率の取得
     * @return 最小拡大率
     */
    getMinScale() {
      return this._minScale;
    }
    /**
     * 拡大率が最大になっているかを確認する
     *
     * @return true 拡大率は最大
     * @return false 拡大率は最大ではない
     */
    isMaxScale() {
      return this.getScaleX() >= this._maxScale;
    }
    /**
     * 拡大率が最小になっているかを確認する
     *
     * @return true 拡大率は最小
     * @return false 拡大率は最小ではない
     */
    isMinScale() {
      return this.getScaleX() <= this._minScale;
    }
    /**
     * デバイスに対応する論理座標の左辺のＸ軸位置を取得する
     * @return デバイスに対応する論理座標の左辺のX軸位置
     */
    getScreenLeft() {
      return this._screenLeft;
    }
    /**
     * デバイスに対応する論理座標の右辺のＸ軸位置を取得する
     * @return デバイスに対応する論理座標の右辺のX軸位置
     */
    getScreenRight() {
      return this._screenRight;
    }
    /**
     * デバイスに対応する論理座標の下辺のY軸位置を取得する
     * @return デバイスに対応する論理座標の下辺のY軸位置
     */
    getScreenBottom() {
      return this._screenBottom;
    }
    /**
     * デバイスに対応する論理座標の上辺のY軸位置を取得する
     * @return デバイスに対応する論理座標の上辺のY軸位置
     */
    getScreenTop() {
      return this._screenTop;
    }
    /**
     * 左辺のX軸位置の最大値の取得
     * @return 左辺のX軸位置の最大値
     */
    getMaxLeft() {
      return this._maxLeft;
    }
    /**
     * 右辺のX軸位置の最大値の取得
     * @return 右辺のX軸位置の最大値
     */
    getMaxRight() {
      return this._maxRight;
    }
    /**
     * 下辺のY軸位置の最大値の取得
     * @return 下辺のY軸位置の最大値
     */
    getMaxBottom() {
      return this._maxBottom;
    }
    /**
     * 上辺のY軸位置の最大値の取得
     * @return 上辺のY軸位置の最大値
     */
    getMaxTop() {
      return this._maxTop;
    }
    // 拡大率の最小値
  };
  var Live2DCubismFramework41;
  ((Live2DCubismFramework42) => {
    Live2DCubismFramework42.CubismViewMatrix = CubismViewMatrix;
  })(Live2DCubismFramework41 || (Live2DCubismFramework41 = {}));

  // .trellis/workspace/lapp-runtime-src/src/renderer/WebSDK/src/touchmanager.ts
  var TouchManager = class {
    /**
     * コンストラクタ
     */
    constructor() {
      __publicField(this, "_startY");
      // タッチを開始した時のxの値
      __publicField(this, "_startX");
      // タッチを開始した時のyの値
      __publicField(this, "_lastX");
      // シングルタッチ時のxの値
      __publicField(this, "_lastY");
      // シングルタッチ時のyの値
      __publicField(this, "_lastX1");
      // ダブルタッチ時の一つ目のxの値
      __publicField(this, "_lastY1");
      // ダブルタッチ時の一つ目のyの値
      __publicField(this, "_lastX2");
      // ダブルタッチ時の二つ目のxの値
      __publicField(this, "_lastY2");
      // ダブルタッチ時の二つ目のyの値
      __publicField(this, "_lastTouchDistance");
      // 2本以上でタッチしたときの指の距離
      __publicField(this, "_deltaX");
      // 前回の値から今回の値へのxの移動距離。
      __publicField(this, "_deltaY");
      // 前回の値から今回の値へのyの移動距離。
      __publicField(this, "_scale");
      // このフレームで掛け合わせる拡大率。拡大操作中以外は1。
      __publicField(this, "_touchSingle");
      // シングルタッチ時はtrue
      __publicField(this, "_flipAvailable");
      this._startX = 0;
      this._startY = 0;
      this._lastX = 0;
      this._lastY = 0;
      this._lastX1 = 0;
      this._lastY1 = 0;
      this._lastX2 = 0;
      this._lastY2 = 0;
      this._lastTouchDistance = 0;
      this._deltaX = 0;
      this._deltaY = 0;
      this._scale = 1;
      this._touchSingle = false;
      this._flipAvailable = false;
    }
    getCenterX() {
      return this._lastX;
    }
    getCenterY() {
      return this._lastY;
    }
    getDeltaX() {
      return this._deltaX;
    }
    getDeltaY() {
      return this._deltaY;
    }
    getStartX() {
      return this._startX;
    }
    getStartY() {
      return this._startY;
    }
    getScale() {
      return this._scale;
    }
    getX() {
      return this._lastX;
    }
    getY() {
      return this._lastY;
    }
    getX1() {
      return this._lastX1;
    }
    getY1() {
      return this._lastY1;
    }
    getX2() {
      return this._lastX2;
    }
    getY2() {
      return this._lastY2;
    }
    isSingleTouch() {
      return this._touchSingle;
    }
    isFlickAvailable() {
      return this._flipAvailable;
    }
    disableFlick() {
      this._flipAvailable = false;
    }
    /**
     * タッチ開始時イベント
     * @param deviceX タッチした画面のxの値
     * @param deviceY タッチした画面のyの値
     */
    touchesBegan(deviceX, deviceY) {
      this._lastX = deviceX;
      this._lastY = deviceY;
      this._startX = deviceX;
      this._startY = deviceY;
      this._lastTouchDistance = -1;
      this._flipAvailable = true;
      this._touchSingle = true;
    }
    /**
     * ドラッグ時のイベント
     * @param deviceX タッチした画面のxの値
     * @param deviceY タッチした画面のyの値
     */
    touchesMoved(deviceX, deviceY) {
      this._lastX = deviceX;
      this._lastY = deviceY;
      this._lastTouchDistance = -1;
      this._touchSingle = true;
    }
    /**
     * フリックの距離測定
     * @return フリック距離
     */
    getFlickDistance() {
      return this.calculateDistance(
        this._startX,
        this._startY,
        this._lastX,
        this._lastY
      );
    }
    /**
     * 点１から点２への距離を求める
     *
     * @param x1 １つ目のタッチした画面のxの値
     * @param y1 １つ目のタッチした画面のyの値
     * @param x2 ２つ目のタッチした画面のxの値
     * @param y2 ２つ目のタッチした画面のyの値
     */
    calculateDistance(x1, y1, x2, y2) {
      return Math.sqrt((x1 - x2) * (x1 - x2) + (y1 - y2) * (y1 - y2));
    }
    /**
     * ２つ目の値から、移動量を求める。
     * 違う方向の場合は移動量０。同じ方向の場合は、絶対値が小さい方の値を参照する。
     *
     * @param v1 １つ目の移動量
     * @param v2 ２つ目の移動量
     *
     * @return 小さい方の移動量
     */
    calculateMovingAmount(v1, v2) {
      if (v1 > 0 != v2 > 0) {
        return 0;
      }
      const sign2 = v1 > 0 ? 1 : -1;
      const absoluteValue1 = Math.abs(v1);
      const absoluteValue2 = Math.abs(v2);
      return sign2 * (absoluteValue1 < absoluteValue2 ? absoluteValue1 : absoluteValue2);
    }
    // フリップが有効かどうか
  };

  // .trellis/workspace/lapp-runtime-src/src/renderer/WebSDK/src/lappview.ts
  var LAppView = class {
    /**
     * コンストラクタ
     */
    constructor() {
      __publicField(this, "_touchManager");
      // タッチマネージャー
      __publicField(this, "_deviceToScreen");
      // デバイスからスクリーンへの行列
      __publicField(this, "_viewMatrix");
      // viewMatrix
      __publicField(this, "_programId");
      // シェーダID
      __publicField(this, "_back");
      // 背景画像
      // _gear: LAppSprite; // ギア画像
      __publicField(this, "_changeModel");
      // モデル切り替えフラグ
      __publicField(this, "_isClick");
      this._programId = null;
      this._back = null;
      this._touchManager = new TouchManager();
      this._deviceToScreen = new CubismMatrix44();
      this._viewMatrix = new CubismViewMatrix();
    }
    /**
     * 初期化する。
     */
    initialize() {
      if (!canvas) {
        console.warn("Canvas is null, cannot initialize LAppView");
        return;
      }
      const { width, height } = canvas;
      const ratio = width / height;
      const left = -ratio;
      const right = ratio;
      const bottom = ViewLogicalLeft;
      const top = ViewLogicalRight;
      this._viewMatrix.setScreenRect(left, right, bottom, top);
      this._viewMatrix.scale(ViewScale, ViewScale);
      this._deviceToScreen.loadIdentity();
      if (width > height) {
        const screenW = Math.abs(right - left);
        this._deviceToScreen.scaleRelative(screenW / width, -screenW / width);
      } else {
        const screenH = Math.abs(top - bottom);
        this._deviceToScreen.scaleRelative(screenH / height, -screenH / height);
      }
      this._deviceToScreen.translateRelative(-width * 0.5, -height * 0.5);
      this._viewMatrix.setMaxScale(ViewMaxScale);
      this._viewMatrix.setMinScale(ViewMinScale);
      this._viewMatrix.setMaxScreenRect(
        ViewLogicalMaxLeft,
        ViewLogicalMaxRight,
        ViewLogicalMaxBottom,
        ViewLogicalMaxTop
      );
    }
    /**
     * 解放する
     */
    release() {
      this._viewMatrix = null;
      this._touchManager = null;
      this._deviceToScreen = null;
      this._back.release();
      this._back = null;
      gl.deleteProgram(this._programId);
      this._programId = null;
    }
    /**
     * 描画する。
     */
    render() {
      gl.useProgram(this._programId);
      if (this._back) {
        this._back.render(this._programId);
      }
      gl.flush();
      const live2DManager = LAppLive2DManager.getInstance();
      live2DManager.setViewMatrix(this._viewMatrix);
      live2DManager.onUpdate();
    }
    /**
     * 画像の初期化を行う。
     */
    initializeSprite() {
      const width = canvas.width;
      const height = canvas.height;
      const textureManager = LAppDelegate.getInstance().getTextureManager();
      const resourcesPath = ResourcesPath;
      let imageName = "";
      imageName = BackImageName;
      if (this._programId == null) {
        this._programId = LAppDelegate.getInstance().createShader();
      }
    }
    /**
     * タッチされた時に呼ばれる。
     *
     * @param pointX スクリーンX座標
     * @param pointY スクリーンY座標
     */
    onTouchesBegan(pointX, pointY) {
      this._touchManager.touchesBegan(
        pointX * window.devicePixelRatio,
        pointY * window.devicePixelRatio
      );
    }
    /**
     * タッチしているときにポインタが動いたら呼ばれる。
     *
     * @param pointX スクリーンX座標
     * @param pointY スクリーンY座標
     */
    onTouchesMoved(pointX, pointY) {
      const viewX = this.transformViewX(this._touchManager.getX());
      const viewY = this.transformViewY(this._touchManager.getY());
      this._touchManager.touchesMoved(
        pointX * window.devicePixelRatio,
        pointY * window.devicePixelRatio
      );
      const live2DManager = LAppLive2DManager.getInstance();
      live2DManager.onDrag(viewX, viewY);
    }
    /**
     * タッチが終了したら呼ばれる。
     *
     * @param pointX スクリーンX座標
     * @param pointY スクリーンY座標
     */
    onTouchesEnded(pointX, pointY) {
      const live2DManager = LAppLive2DManager.getInstance();
      live2DManager.onDrag(0, 0);
      {
        const x = this._deviceToScreen.transformX(
          this._touchManager.getX()
        );
        const y = this._deviceToScreen.transformY(
          this._touchManager.getY()
        );
        if (DebugTouchLogEnable) {
          LAppPal.printMessage(`[APP]touchesEnded x: ${x} y: ${y}`);
        }
        live2DManager.onTap(x, y);
      }
    }
    /**
     * X座標をView座標に変換する。
     *
     * @param deviceX デバイスX座標
     */
    transformViewX(deviceX) {
      const screenX = this._deviceToScreen.transformX(deviceX);
      return this._viewMatrix.invertTransformX(screenX);
    }
    /**
     * Y座標をView座標に変換する。
     *
     * @param deviceY デバイスY座標
     */
    transformViewY(deviceY) {
      const screenY = this._deviceToScreen.transformY(deviceY);
      return this._viewMatrix.invertTransformY(screenY);
    }
    /**
     * X座標をScreen座標に変換する。
     * @param deviceX デバイスX座標
     */
    transformScreenX(deviceX) {
      return this._deviceToScreen.transformX(deviceX);
    }
    /**
     * Y座標をScreen座標に変換する。
     *
     * @param deviceY デバイスY座標
     */
    transformScreenY(deviceY) {
      return this._deviceToScreen.transformY(deviceY);
    }
    // クリック中
  };

  // .trellis/workspace/lapp-runtime-src/src/renderer/WebSDK/src/lappdelegate.ts
  var s_instance3 = null;
  var frameBuffer = null;
  var LAppDelegate = class _LAppDelegate {
    /**
     * コンストラクタ
     * 构造函数
     */
    constructor() {
      __publicField(this, "_cubismOption");
      // Cubism SDK Option
      __publicField(this, "_view");
      // View情報  // 视图信息
      __publicField(this, "_captured");
      // クリックしているか // 是否点击
      __publicField(this, "_mouseX");
      // マウスX座標 // 鼠标X坐标
      __publicField(this, "_mouseY");
      // マウスY座標 // 鼠标Y坐标
      __publicField(this, "_isEnd");
      // APP終了しているか // APP是否已结束
      __publicField(this, "_textureManager");
      this._captured = false;
      this._mouseX = 0;
      this._mouseY = 0;
      this._isEnd = false;
      this._cubismOption = new Option();
      this._view = new LAppView();
      this._textureManager = new LAppTextureManager();
    }
    /**
     * クラスのインスタンス（シングルトン）を返す。
     * インスタンスが生成されていない場合は内部でインスタンスを生成する。
     * 
     * 返回类的实例（单例）。
     * 如果尚未创建实例，则在内部创建实例。
     *
     * @return クラスのインスタンス
     */
    static getInstance() {
      if (s_instance3 == null) {
        s_instance3 = new _LAppDelegate();
      }
      return s_instance3;
    }
    /**
     * クラスのインスタンス（シングルトン）を解放する。
     * 
     * 释放类的实例（单例）。
     * 
     */
    static releaseInstance() {
      if (s_instance3 != null) {
        s_instance3.release();
      }
      s_instance3 = null;
    }
    /**
     * Initialize the application.
     */
    initialize() {
      if (CanvasSize === "auto") {
        this._resizeCanvas();
      } else {
        canvas.width = CanvasSize.width;
        canvas.height = CanvasSize.height;
      }
      if (!frameBuffer) {
        frameBuffer = gl.getParameter(gl.FRAMEBUFFER_BINDING);
      }
      gl.enable(gl.BLEND);
      gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);
      const supportTouch = "ontouchend" in canvas;
      if (supportTouch) {
        canvas.addEventListener("touchstart", onTouchBegan, { passive: true });
        canvas.addEventListener("touchmove", onTouchMoved, { passive: true });
        canvas.addEventListener("touchend", onTouchEnded, { passive: true });
        canvas.addEventListener("touchcancel", onTouchCancel, { passive: true });
      } else {
        canvas.addEventListener("mousedown", onClickBegan, { passive: true });
        canvas.addEventListener("mousemove", onMouseMoved, { passive: true });
        canvas.addEventListener("mouseup", onClickEnded, { passive: true });
      }
      this._view.initialize();
      this.initializeCubism();
      return true;
    }
    /**
     * Resize canvas and re-initialize view.
     */
    onResize() {
      this._resizeCanvas();
      if (this._view && canvas) {
        this._view.initialize();
        this._view.initializeSprite();
        const manager = LAppLive2DManager.getInstance();
        if (manager) {
          const model = manager.getModel(0);
          if (model) {
            const width = canvas.width;
            const height = canvas.height;
            if (width > 0 && height > 0) {
              if (model.setPosition) {
                model.setPosition(width / 2, height / 2);
              }
            }
          }
        }
      }
    }
    /**
     * 解放する。
     */
    release() {
      this._textureManager.release();
      this._textureManager = null;
      this._view.release();
      this._view = null;
      LAppLive2DManager.releaseInstance();
      CubismFramework.dispose();
    }
    /**
     * 実行処理。
     * 执行处理。
     */
    run() {
      const loop = () => {
        if (s_instance3 == null) {
          return;
        }
        if (ENABLE_LIMITED_FRAME_RATE) {
          LAppPal.updateTime(false);
          if (LAppPal.getDeltaTime() < 1 / LIMITED_FRAME_RATE) {
            requestAnimationFrame(loop);
            return;
          }
        }
        LAppPal.updateTime(true);
        gl.clearColor(0, 0, 0, 1);
        gl.enable(gl.DEPTH_TEST);
        gl.depthFunc(gl.LEQUAL);
        gl.clear(gl.DEPTH_BUFFER_BIT);
        gl.clearDepth(1);
        gl.enable(gl.BLEND);
        gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);
        this._view.render();
        requestAnimationFrame(loop);
      };
      loop();
    }
    /**
     * シェーダーを登録する。
     * 注册着色器。
     */
    createShader() {
      const vertexShaderId = gl.createShader(gl.VERTEX_SHADER);
      if (vertexShaderId == null) {
        LAppPal.printMessage("failed to create vertexShader");
        return null;
      }
      const vertexShader = "precision mediump float;attribute vec3 position;attribute vec2 uv;varying vec2 vuv;void main(void){   gl_Position = vec4(position, 1.0);   vuv = uv;}";
      gl.shaderSource(vertexShaderId, vertexShader);
      gl.compileShader(vertexShaderId);
      const fragmentShaderId = gl.createShader(gl.FRAGMENT_SHADER);
      if (fragmentShaderId == null) {
        LAppPal.printMessage("failed to create fragmentShader");
        return null;
      }
      const fragmentShader = "precision mediump float;varying vec2 vuv;uniform sampler2D texture;void main(void){   gl_FragColor = texture2D(texture, vuv);}";
      gl.shaderSource(fragmentShaderId, fragmentShader);
      gl.compileShader(fragmentShaderId);
      const programId = gl.createProgram();
      gl.attachShader(programId, vertexShaderId);
      gl.attachShader(programId, fragmentShaderId);
      gl.deleteShader(vertexShaderId);
      gl.deleteShader(fragmentShaderId);
      gl.linkProgram(programId);
      gl.useProgram(programId);
      return programId;
    }
    /**
     * View情報を取得する。
     */
    getView() {
      return this._view;
    }
    getTextureManager() {
      return this._textureManager;
    }
    /**
     * Cubism SDKの初期化
     */
    initializeCubism() {
      this._cubismOption.logFunction = LAppPal.printMessage;
      this._cubismOption.loggingLevel = CubismLoggingLevel;
      CubismFramework.startUp(this._cubismOption);
      CubismFramework.initialize();
      LAppLive2DManager.getInstance();
      LAppPal.updateTime();
      this._view.initializeSprite();
    }
    /**
     * Resize the canvas to fill the screen.
     */
    _resizeCanvas() {
      if (!canvas) {
        console.warn("Canvas is null, skipping resize");
        return;
      }
      canvas.width = canvas.clientWidth * window.devicePixelRatio;
      canvas.height = canvas.clientHeight * window.devicePixelRatio;
      if (gl) {
        gl.viewport(0, 0, gl.drawingBufferWidth, gl.drawingBufferHeight);
      }
    }
    // テクスチャマネージャー // 纹理管理器
  };
  function onClickBegan(e) {
    if (!LAppDelegate.getInstance()._view) {
      LAppPal.printMessage("view notfound");
      return;
    }
    LAppDelegate.getInstance()._captured = true;
    const posX = e.pageX;
    const posY = e.pageY;
    LAppDelegate.getInstance()._view.onTouchesBegan(posX, posY);
  }
  function onMouseMoved(e) {
    if (!LAppDelegate.getInstance()._captured) {
      return;
    }
    if (!LAppDelegate.getInstance()._view) {
      LAppPal.printMessage("view notfound");
      return;
    }
    const rect = e.target.getBoundingClientRect();
    const posX = e.clientX - rect.left;
    const posY = e.clientY - rect.top;
    LAppDelegate.getInstance()._view.onTouchesMoved(posX, posY);
  }
  function onClickEnded(e) {
    LAppDelegate.getInstance()._captured = false;
    if (!LAppDelegate.getInstance()._view) {
      LAppPal.printMessage("view notfound");
      return;
    }
    const rect = e.target.getBoundingClientRect();
    const posX = e.clientX - rect.left;
    const posY = e.clientY - rect.top;
    LAppDelegate.getInstance()._view.onTouchesEnded(posX, posY);
  }
  function onTouchBegan(e) {
    if (!LAppDelegate.getInstance()._view) {
      LAppPal.printMessage("view notfound");
      return;
    }
    LAppDelegate.getInstance()._captured = true;
    const posX = e.changedTouches[0].pageX;
    const posY = e.changedTouches[0].pageY;
    LAppDelegate.getInstance()._view.onTouchesBegan(posX, posY);
  }
  function onTouchMoved(e) {
    if (!LAppDelegate.getInstance()._captured) {
      return;
    }
    if (!LAppDelegate.getInstance()._view) {
      LAppPal.printMessage("view notfound");
      return;
    }
    const rect = e.target.getBoundingClientRect();
    const posX = e.changedTouches[0].clientX - rect.left;
    const posY = e.changedTouches[0].clientY - rect.top;
    LAppDelegate.getInstance()._view.onTouchesMoved(posX, posY);
  }
  function onTouchEnded(e) {
    LAppDelegate.getInstance()._captured = false;
    if (!LAppDelegate.getInstance()._view) {
      LAppPal.printMessage("view notfound");
      return;
    }
    const rect = e.target.getBoundingClientRect();
    const posX = e.changedTouches[0].clientX - rect.left;
    const posY = e.changedTouches[0].clientY - rect.top;
    LAppDelegate.getInstance()._view.onTouchesEnded(posX, posY);
  }
  function onTouchCancel(e) {
    LAppDelegate.getInstance()._captured = false;
    if (!LAppDelegate.getInstance()._view) {
      LAppPal.printMessage("view notfound");
      return;
    }
    const rect = e.target.getBoundingClientRect();
    const posX = e.changedTouches[0].clientX - rect.left;
    const posY = e.changedTouches[0].clientY - rect.top;
    LAppDelegate.getInstance()._view.onTouchesEnded(posX, posY);
  }

  // .trellis/workspace/lapp-runtime-src/src/renderer/WebSDK/src/lappwavfilehandler.ts
  var s_instance4 = null;
  var LAppWavFileHandler = class _LAppWavFileHandler {
    constructor() {
      __publicField(this, "_pcmData");
      __publicField(this, "_userTimeSeconds");
      __publicField(this, "_lastRms");
      __publicField(this, "_sampleOffset");
      __publicField(this, "_wavFileInfo");
      __publicField(this, "_byteReader");
      __publicField(this, "_loadFiletoBytes", (arrayBuffer, length) => {
        this._byteReader._fileByte = arrayBuffer;
        this._byteReader._fileDataView = new DataView(this._byteReader._fileByte);
        this._byteReader._fileSize = length;
      });
      this._pcmData = null;
      this._userTimeSeconds = 0;
      this._lastRms = 0;
      this._sampleOffset = 0;
      this._wavFileInfo = new WavFileInfo();
      this._byteReader = new ByteReader();
    }
    /**
     * クラスのインスタンス（シングルトン）を返す。
     * インスタンスが生成されていない場合は内部でインスタンスを生成する。
     *
     * @return クラスのインスタンス
     * @deprecated このクラスでのシングルトンパターンの使用は非推奨となりました。代わりに new LAppWavFileHandler() を使用してください。
     */
    static getInstance() {
      if (s_instance4 == null) {
        s_instance4 = new _LAppWavFileHandler();
      }
      return s_instance4;
    }
    /**
     * クラスのインスタンス（シングルトン）を解放する。
     *
     * @deprecated この関数は getInstance() が非推奨になったことに伴い、非推奨となりました。
     */
    static releaseInstance() {
      if (s_instance4 != null) {
        s_instance4 = void 0;
      }
      s_instance4 = null;
    }
    update(deltaTimeSeconds) {
      let goalOffset;
      let rms;
      if (this._pcmData == null || this._sampleOffset >= this._wavFileInfo._samplesPerChannel) {
        this._lastRms = 0;
        return false;
      }
      this._userTimeSeconds += deltaTimeSeconds;
      goalOffset = Math.floor(
        this._userTimeSeconds * this._wavFileInfo._samplingRate
      );
      if (goalOffset > this._wavFileInfo._samplesPerChannel) {
        goalOffset = this._wavFileInfo._samplesPerChannel;
      }
      rms = 0;
      for (let channelCount = 0; channelCount < this._wavFileInfo._numberOfChannels; channelCount++) {
        for (let sampleCount = this._sampleOffset; sampleCount < goalOffset; sampleCount++) {
          const pcm = this._pcmData[channelCount][sampleCount];
          rms += pcm * pcm;
        }
      }
      rms = Math.sqrt(
        rms / (this._wavFileInfo._numberOfChannels * (goalOffset - this._sampleOffset))
      );
      this._lastRms = rms;
      this._sampleOffset = goalOffset;
      return true;
    }
    start(filePath) {
      this._sampleOffset = 0;
      this._userTimeSeconds = 0;
      this._lastRms = 0;
      this.loadWavFile(filePath);
    }
    getRms() {
      return this._lastRms;
    }
    loadWavFile(filePath) {
      return new Promise((resolveValue) => {
        let ret = false;
        if (this._pcmData != null) {
          this.releasePcmData();
        }
        const asyncFileLoad = async () => {
          return fetch(filePath).then((responce) => {
            return responce.arrayBuffer();
          });
        };
        const asyncWavFileManager = (async () => {
          this._byteReader._fileByte = await asyncFileLoad();
          this._byteReader._fileDataView = new DataView(
            this._byteReader._fileByte
          );
          this._byteReader._fileSize = this._byteReader._fileByte.byteLength;
          this._byteReader._readOffset = 0;
          if (this._byteReader._fileByte == null || this._byteReader._fileSize < 4) {
            resolveValue(false);
            return;
          }
          this._wavFileInfo._fileName = filePath;
          try {
            if (!this._byteReader.getCheckSignature("RIFF")) {
              ret = false;
              throw new Error('Cannot find Signeture "RIFF".');
            }
            this._byteReader.get32LittleEndian();
            if (!this._byteReader.getCheckSignature("WAVE")) {
              ret = false;
              throw new Error('Cannot find Signeture "WAVE".');
            }
            if (!this._byteReader.getCheckSignature("fmt ")) {
              ret = false;
              throw new Error('Cannot find Signeture "fmt".');
            }
            const fmtChunkSize = this._byteReader.get32LittleEndian();
            if (this._byteReader.get16LittleEndian() != 1) {
              ret = false;
              throw new Error("File is not linear PCM.");
            }
            this._wavFileInfo._numberOfChannels = this._byteReader.get16LittleEndian();
            this._wavFileInfo._samplingRate = this._byteReader.get32LittleEndian();
            this._byteReader.get32LittleEndian();
            this._byteReader.get16LittleEndian();
            this._wavFileInfo._bitsPerSample = this._byteReader.get16LittleEndian();
            if (fmtChunkSize > 16) {
              this._byteReader._readOffset += fmtChunkSize - 16;
            }
            while (!this._byteReader.getCheckSignature("data") && this._byteReader._readOffset < this._byteReader._fileSize) {
              this._byteReader._readOffset += this._byteReader.get32LittleEndian() + 4;
            }
            if (this._byteReader._readOffset >= this._byteReader._fileSize) {
              ret = false;
              throw new Error('Cannot find "data" Chunk.');
            }
            {
              const dataChunkSize = this._byteReader.get32LittleEndian();
              this._wavFileInfo._samplesPerChannel = dataChunkSize * 8 / (this._wavFileInfo._bitsPerSample * this._wavFileInfo._numberOfChannels);
            }
            this._pcmData = new Array(this._wavFileInfo._numberOfChannels);
            for (let channelCount = 0; channelCount < this._wavFileInfo._numberOfChannels; channelCount++) {
              this._pcmData[channelCount] = new Float32Array(
                this._wavFileInfo._samplesPerChannel
              );
            }
            for (let sampleCount = 0; sampleCount < this._wavFileInfo._samplesPerChannel; sampleCount++) {
              for (let channelCount = 0; channelCount < this._wavFileInfo._numberOfChannels; channelCount++) {
                this._pcmData[channelCount][sampleCount] = this.getPcmSample();
              }
            }
            ret = true;
            resolveValue(ret);
          } catch (e) {
            console.log(e);
          }
        })().then(() => {
          resolveValue(ret);
        });
      });
    }
    getPcmSample() {
      let pcm32;
      switch (this._wavFileInfo._bitsPerSample) {
        case 8:
          pcm32 = this._byteReader.get8() - 128;
          pcm32 <<= 24;
          break;
        case 16:
          pcm32 = this._byteReader.get16LittleEndian() << 16;
          break;
        case 24:
          pcm32 = this._byteReader.get24LittleEndian() << 8;
          break;
        default:
          pcm32 = 0;
          break;
      }
      return pcm32 / 2147483647;
    }
    /**
     * 指定したチャンネルから音声サンプルの配列を取得する
     *
     * @param usechannel 利用するチャンネル
     * @returns 指定したチャンネルの音声サンプルの配列
     */
    getPcmDataChannel(usechannel) {
      if (!this._pcmData || !(usechannel < this._pcmData.length)) {
        return null;
      }
      return Float32Array.from(this._pcmData[usechannel]);
    }
    /**
     * 音声のサンプリング周波数を取得する。
     *
     * @returns 音声のサンプリング周波数
     */
    getWavSamplingRate() {
      if (!this._wavFileInfo || this._wavFileInfo._samplingRate < 1) {
        return null;
      }
      return this._wavFileInfo._samplingRate;
    }
    releasePcmData() {
      if (this._pcmData) {
        for (let channelCount = 0; channelCount < this._wavFileInfo._numberOfChannels; channelCount++) {
          this._pcmData[channelCount] = void 0;
        }
        this._pcmData = null;
      }
    }
  };
  var WavFileInfo = class {
    constructor() {
      __publicField(this, "_fileName");
      ///< ファイル名
      __publicField(this, "_numberOfChannels");
      ///< チャンネル数
      __publicField(this, "_bitsPerSample");
      ///< サンプルあたりビット数
      __publicField(this, "_samplingRate");
      ///< サンプリングレート
      __publicField(this, "_samplesPerChannel");
      this._fileName = "";
      this._numberOfChannels = 0;
      this._bitsPerSample = 0;
      this._samplingRate = 0;
      this._samplesPerChannel = 0;
    }
    ///< 1チャンネルあたり総サンプル数
  };
  var ByteReader = class {
    constructor() {
      __publicField(this, "_fileByte");
      ///< ロードしたファイルのバイト列
      __publicField(this, "_fileDataView");
      __publicField(this, "_fileSize");
      ///< ファイルサイズ
      __publicField(this, "_readOffset");
      this._fileByte = null;
      this._fileDataView = null;
      this._fileSize = 0;
      this._readOffset = 0;
    }
    /**
     * @brief 8ビット読み込み
     * @return Csm::csmUint8 読み取った8ビット値
     */
    get8() {
      const ret = this._fileDataView.getUint8(this._readOffset);
      this._readOffset++;
      return ret;
    }
    /**
     * @brief 16ビット読み込み（リトルエンディアン）
     * @return Csm::csmUint16 読み取った16ビット値
     */
    get16LittleEndian() {
      const ret = this._fileDataView.getUint8(this._readOffset + 1) << 8 | this._fileDataView.getUint8(this._readOffset);
      this._readOffset += 2;
      return ret;
    }
    /**
     * @brief 24ビット読み込み（リトルエンディアン）
     * @return Csm::csmUint32 読み取った24ビット値（下位24ビットに設定）
     */
    get24LittleEndian() {
      const ret = this._fileDataView.getUint8(this._readOffset + 2) << 16 | this._fileDataView.getUint8(this._readOffset + 1) << 8 | this._fileDataView.getUint8(this._readOffset);
      this._readOffset += 3;
      return ret;
    }
    /**
     * @brief 32ビット読み込み（リトルエンディアン）
     * @return Csm::csmUint32 読み取った32ビット値
     */
    get32LittleEndian() {
      const ret = this._fileDataView.getUint8(this._readOffset + 3) << 24 | this._fileDataView.getUint8(this._readOffset + 2) << 16 | this._fileDataView.getUint8(this._readOffset + 1) << 8 | this._fileDataView.getUint8(this._readOffset);
      this._readOffset += 4;
      return ret;
    }
    /**
     * @brief シグネチャの取得と参照文字列との一致チェック
     * @param[in] reference 検査対象のシグネチャ文字列
     * @retval  true    一致している
     * @retval  false   一致していない
     */
    getCheckSignature(reference) {
      const getSignature = new Uint8Array(4);
      const referenceString = new TextEncoder().encode(reference);
      if (reference.length != 4) {
        return false;
      }
      for (let signatureOffset = 0; signatureOffset < 4; signatureOffset++) {
        getSignature[signatureOffset] = this.get8();
      }
      return getSignature[0] == referenceString[0] && getSignature[1] == referenceString[1] && getSignature[2] == referenceString[2] && getSignature[3] == referenceString[3];
    }
    ///< ファイル参照位置
  };

  // .trellis/workspace/lapp-runtime-src/src/renderer/WebSDK/src/lappmodel.ts
  var LAppModel = class extends CubismUserModel {
    /**
     * コンストラクタ
     */
    constructor() {
      super();
      __publicField(this, "_modelSetting");
      // モデルセッティング情報
      __publicField(this, "_modelHomeDir");
      // モデルセッティングが置かれたディレクトリ
      __publicField(this, "_userTimeSeconds");
      // デルタ時間の積算値[秒]
      __publicField(this, "_eyeBlinkIds");
      // モデルに設定された瞬き機能用パラメータID
      __publicField(this, "_lipSyncIds");
      // モデルに設定されたリップシンク機能用パラメータID
      __publicField(this, "_motions");
      // 読み込まれているモーションのリスト
      __publicField(this, "_expressions");
      // 読み込まれている表情のリスト
      __publicField(this, "_hitArea");
      __publicField(this, "_userArea");
      __publicField(this, "_idParamAngleX");
      // パラメータID: ParamAngleX
      __publicField(this, "_idParamAngleY");
      // パラメータID: ParamAngleY
      __publicField(this, "_idParamAngleZ");
      // パラメータID: ParamAngleZ
      __publicField(this, "_idParamEyeBallX");
      // パラメータID: ParamEyeBallX
      __publicField(this, "_idParamEyeBallY");
      // パラメータID: ParamEyeBAllY
      __publicField(this, "_idParamBodyAngleX");
      // パラメータID: ParamBodyAngleX
      __publicField(this, "_state");
      // 現在のステータス管理用
      __publicField(this, "_expressionCount");
      // 表情データカウント
      __publicField(this, "_textureCount");
      // テクスチャカウント
      __publicField(this, "_motionCount");
      // モーションデータカウント
      __publicField(this, "_allMotionCount");
      // モーション総数
      __publicField(this, "_wavFileHandler");
      //wavファイルハンドラ
      __publicField(this, "_externalLipSyncValue");
      // Browser playback lip-sync value supplied by the Rikka overlay.
      __publicField(this, "_externalEyeBlinkValue");
      // Natural blink value supplied by the Rikka overlay.
      __publicField(this, "_consistency");
      this._modelSetting = null;
      this._modelHomeDir = null;
      this._userTimeSeconds = 0;
      this._eyeBlinkIds = new csmVector();
      this._lipSyncIds = new csmVector();
      this._motions = new csmMap();
      this._expressions = new csmMap();
      this._hitArea = new csmVector();
      this._userArea = new csmVector();
      const idManager = CubismFramework.getIdManager();
      if (idManager) {
        this._idParamAngleX = idManager.getId(
          CubismDefaultParameterId.ParamAngleX
        );
        this._idParamAngleY = idManager.getId(
          CubismDefaultParameterId.ParamAngleY
        );
        this._idParamAngleZ = idManager.getId(
          CubismDefaultParameterId.ParamAngleZ
        );
        this._idParamEyeBallX = idManager.getId(
          CubismDefaultParameterId.ParamEyeBallX
        );
        this._idParamEyeBallY = idManager.getId(
          CubismDefaultParameterId.ParamEyeBallY
        );
        this._idParamBodyAngleX = idManager.getId(
          CubismDefaultParameterId.ParamBodyAngleX
        );
      } else {
        this._idParamAngleX = null;
        this._idParamAngleY = null;
        this._idParamAngleZ = null;
        this._idParamEyeBallX = null;
        this._idParamEyeBallY = null;
        this._idParamBodyAngleX = null;
      }
      if (MOCConsistencyValidationEnable) {
        this._mocConsistency = true;
      }
      this._state = 0 /* LoadAssets */;
      this._expressionCount = 0;
      this._textureCount = 0;
      this._motionCount = 0;
      this._allMotionCount = 0;
      this._wavFileHandler = new LAppWavFileHandler();
      this._externalLipSyncValue = null;
      this._externalEyeBlinkValue = null;
      this._consistency = false;
    }
    /**
     * model3.jsonが置かれたディレクトリとファイルパスからモデルを生成する
     * @param dir
     * @param fileName
     */
    loadAssets(dir, fileName) {
      this._modelHomeDir = dir;
      fetch(`${this._modelHomeDir}${fileName}`).then((response) => response.arrayBuffer()).then((arrayBuffer) => {
        const setting = new CubismModelSettingJson(
          arrayBuffer,
          arrayBuffer.byteLength
        );
        this._state = 1 /* LoadModel */;
        this.setupModel(setting);
      }).catch((error) => {
        CubismLogError(`Failed to load file ${this._modelHomeDir}${fileName}`);
      });
    }
    /**
     * model3.jsonからモデルを生成する。
     * model3.jsonの記述に従ってモデル生成、モーション、物理演算などのコンポーネント生成を行う。
     *
     * @param setting ICubismModelSettingのインスタンス
     */
    setupModel(setting) {
      this._updating = true;
      this._initialized = false;
      this._modelSetting = setting;
      const hitAreasCount = this._modelSetting.getHitAreasCount();
      console.log(`Model has ${hitAreasCount} hit areas`);
      if (this._modelSetting.getModelFileName() != "") {
        const modelFileName = this._modelSetting.getModelFileName();
        fetch(`${this._modelHomeDir}${modelFileName}`).then((response) => {
          if (response.ok) {
            return response.arrayBuffer();
          } else if (response.status >= 400) {
            CubismLogError(
              `Failed to load file ${this._modelHomeDir}${modelFileName}`
            );
            return new ArrayBuffer(0);
          }
        }).then((arrayBuffer) => {
          this.loadModel(arrayBuffer, this._mocConsistency, CurrentKScale);
          this._state = 3 /* LoadExpression */;
          loadCubismExpression();
        });
        this._state = 2 /* WaitLoadModel */;
      } else {
        LAppPal.printMessage("Model data does not exist.");
      }
      const loadCubismExpression = () => {
        if (this._modelSetting.getExpressionCount() > 0) {
          const count = this._modelSetting.getExpressionCount();
          for (let i = 0; i < count; i++) {
            const expressionName = this._modelSetting.getExpressionName(i);
            const expressionFileName = this._modelSetting.getExpressionFileName(i);
            fetch(`${this._modelHomeDir}${expressionFileName}`).then((response) => {
              if (response.ok) {
                return response.arrayBuffer();
              } else if (response.status >= 400) {
                CubismLogError(
                  `Failed to load file ${this._modelHomeDir}${expressionFileName}`
                );
                return new ArrayBuffer(0);
              }
            }).then((arrayBuffer) => {
              const motion = this.loadExpression(
                arrayBuffer,
                arrayBuffer.byteLength,
                expressionName
              );
              if (this._expressions.getValue(expressionName) != null) {
                ACubismMotion.delete(
                  this._expressions.getValue(expressionName)
                );
                this._expressions.setValue(expressionName, null);
              }
              this._expressions.setValue(expressionName, motion);
              this._expressionCount++;
              if (this._expressionCount >= count) {
                this._state = 5 /* LoadPhysics */;
                loadCubismPhysics();
              }
            });
          }
          this._state = 4 /* WaitLoadExpression */;
        } else {
          this._state = 5 /* LoadPhysics */;
          loadCubismPhysics();
        }
      };
      const loadCubismPhysics = () => {
        if (this._modelSetting.getPhysicsFileName() != "") {
          const physicsFileName = this._modelSetting.getPhysicsFileName();
          fetch(`${this._modelHomeDir}${physicsFileName}`).then((response) => {
            if (response.ok) {
              return response.arrayBuffer();
            } else if (response.status >= 400) {
              CubismLogError(
                `Failed to load file ${this._modelHomeDir}${physicsFileName}`
              );
              return new ArrayBuffer(0);
            }
          }).then((arrayBuffer) => {
            this.loadPhysics(arrayBuffer, arrayBuffer.byteLength);
            this._state = 7 /* LoadPose */;
            loadCubismPose();
          });
          this._state = 6 /* WaitLoadPhysics */;
        } else {
          this._state = 7 /* LoadPose */;
          loadCubismPose();
        }
      };
      const loadCubismPose = () => {
        if (this._modelSetting.getPoseFileName() != "") {
          const poseFileName = this._modelSetting.getPoseFileName();
          fetch(`${this._modelHomeDir}${poseFileName}`).then((response) => {
            if (response.ok) {
              return response.arrayBuffer();
            } else if (response.status >= 400) {
              CubismLogError(
                `Failed to load file ${this._modelHomeDir}${poseFileName}`
              );
              return new ArrayBuffer(0);
            }
          }).then((arrayBuffer) => {
            this.loadPose(arrayBuffer, arrayBuffer.byteLength);
            this._state = 9 /* SetupEyeBlink */;
            setupEyeBlink();
          });
          this._state = 8 /* WaitLoadPose */;
        } else {
          this._state = 9 /* SetupEyeBlink */;
          setupEyeBlink();
        }
      };
      const setupEyeBlink = () => {
        if (this._modelSetting.getEyeBlinkParameterCount() > 0) {
          this._eyeBlink = CubismEyeBlink.create(this._modelSetting);
          this._state = 10 /* SetupBreath */;
        }
        setupBreath();
      };
      const setupBreath = () => {
        this._breath = CubismBreath.create();
        const breathParameters = new csmVector();
        breathParameters.pushBack(
          new BreathParameterData(this._idParamAngleX, 0, 15, 6.5345, 0.5)
        );
        breathParameters.pushBack(
          new BreathParameterData(this._idParamAngleY, 0, 8, 3.5345, 0.5)
        );
        breathParameters.pushBack(
          new BreathParameterData(this._idParamAngleZ, 0, 10, 5.5345, 0.5)
        );
        breathParameters.pushBack(
          new BreathParameterData(this._idParamBodyAngleX, 0, 4, 15.5345, 0.5)
        );
        const idManager = CubismFramework.getIdManager();
        if (idManager) {
          const breathParameterId = idManager.getId(CubismDefaultParameterId.ParamBreath);
          if (breathParameterId) {
            breathParameters.pushBack(
              new BreathParameterData(breathParameterId, 0.5, 0.5, 3.2345, 1)
            );
          }
        }
        this._breath.setParameters(breathParameters);
        this._state = 11 /* LoadUserData */;
        loadUserData();
      };
      const loadUserData = () => {
        if (this._modelSetting.getUserDataFile() != "") {
          const userDataFile = this._modelSetting.getUserDataFile();
          fetch(`${this._modelHomeDir}${userDataFile}`).then((response) => {
            if (response.ok) {
              return response.arrayBuffer();
            } else if (response.status >= 400) {
              CubismLogError(
                `Failed to load file ${this._modelHomeDir}${userDataFile}`
              );
              return new ArrayBuffer(0);
            }
          }).then((arrayBuffer) => {
            this.loadUserData(arrayBuffer, arrayBuffer.byteLength);
            this._state = 13 /* SetupEyeBlinkIds */;
            setupEyeBlinkIds();
          });
          this._state = 12 /* WaitLoadUserData */;
        } else {
          this._state = 13 /* SetupEyeBlinkIds */;
          setupEyeBlinkIds();
        }
      };
      const setupEyeBlinkIds = () => {
        const eyeBlinkIdCount = this._modelSetting.getEyeBlinkParameterCount();
        for (let i = 0; i < eyeBlinkIdCount; ++i) {
          this._eyeBlinkIds.pushBack(
            this._modelSetting.getEyeBlinkParameterId(i)
          );
        }
        this._state = 14 /* SetupLipSyncIds */;
        setupLipSyncIds();
      };
      const setupLipSyncIds = () => {
        const lipSyncIdCount = this._modelSetting.getLipSyncParameterCount();
        for (let i = 0; i < lipSyncIdCount; ++i) {
          this._lipSyncIds.pushBack(this._modelSetting.getLipSyncParameterId(i));
        }
        if (this._lipSyncIds.getSize() === 0) {
          console.warn('[Fallback] No LipSync IDs defined in model setting. Attempting fallback to "ParamMouthOpenY".');
          const idManager = CubismFramework.getIdManager();
          if (idManager) {
            const fallbackId = idManager.getId(CubismDefaultParameterId.ParamMouthOpenY);
            if (this._model && fallbackId && this._model.getParameterIndex(fallbackId) !== -1) {
              this._lipSyncIds.pushBack(fallbackId);
              console.log('[Fallback] Successfully added "ParamMouthOpenY" as LipSync ID.');
            } else {
              console.warn('[Fallback] Fallback ID "ParamMouthOpenY" not found in the current model or model not loaded.');
            }
          } else {
            console.warn("[Fallback] Could not access IdManager. LipSync fallback unavailable.");
          }
        }
        this._state = 15 /* SetupLayout */;
        setupLayout();
      };
      const setupLayout = () => {
        const layout = new csmMap();
        if (this._modelSetting == null || this._modelMatrix == null) {
          CubismLogError("Failed to setupLayout().");
          return;
        }
        this._modelSetting.getLayoutMap(layout);
        this._modelMatrix.setupFromLayout(layout);
        this._state = 16 /* LoadMotion */;
        loadCubismMotion();
      };
      const loadCubismMotion = () => {
        this._state = 17 /* WaitLoadMotion */;
        this._model.saveParameters();
        this._allMotionCount = 0;
        this._motionCount = 0;
        const group = [];
        const motionGroupCount = this._modelSetting.getMotionGroupCount();
        for (let i = 0; i < motionGroupCount; i++) {
          group[i] = this._modelSetting.getMotionGroupName(i);
          this._allMotionCount += this._modelSetting.getMotionCount(group[i]);
        }
        if (this._allMotionCount == 0) {
          this._state = 20 /* LoadTexture */;
          this._motionManager.stopAllMotions();
          this._updating = false;
          this._initialized = true;
          this.createRenderer();
          this.setupTextures();
          this.getRenderer().startUp(gl);
          return;
        }
        for (let i = 0; i < motionGroupCount; i++) {
          this.preLoadMotionGroup(group[i]);
        }
        if (motionGroupCount == 0) {
          this._state = 20 /* LoadTexture */;
          this._motionManager.stopAllMotions();
          this._updating = false;
          this._initialized = true;
          this.createRenderer();
          this.setupTextures();
          this.getRenderer().startUp(gl);
        }
      };
    }
    /**
     * テクスチャのセットアップ
     */
    setupTextures() {
      console.log("Setting up textures for model:", this._modelHomeDir);
      const usePremultiply = true;
      if (this._state == 20 /* LoadTexture */) {
        const textureCount = this._modelSetting.getTextureCount();
        for (let modelTextureNumber = 0; modelTextureNumber < textureCount; modelTextureNumber++) {
          if (this._modelSetting.getTextureFileName(modelTextureNumber) == "") {
            console.log("getTextureFileName null");
            continue;
          }
          let texturePath = this._modelSetting.getTextureFileName(modelTextureNumber);
          texturePath = this._modelHomeDir + texturePath;
          const onLoad = (textureInfo) => {
            this.getRenderer().bindTexture(modelTextureNumber, textureInfo.id);
            this._textureCount++;
            if (this._textureCount >= textureCount) {
              this._state = 22 /* CompleteSetup */;
            }
          };
          LAppDelegate.getInstance().getTextureManager().createTextureFromPngFile(texturePath, usePremultiply, onLoad);
          this.getRenderer().setIsPremultipliedAlpha(usePremultiply);
        }
        this._state = 21 /* WaitLoadTexture */;
      }
    }
    /**
     * レンダラを再構築する
     */
    reloadRenderer() {
      this.deleteRenderer();
      this.createRenderer();
      this.setupTextures();
    }
    /**
     * 更新
     */
    update() {
      if (this._state != 22 /* CompleteSetup */) return;
      const deltaTimeSeconds = LAppPal.getDeltaTime();
      this._userTimeSeconds += deltaTimeSeconds;
      this._dragManager.update(deltaTimeSeconds);
      this._dragX = this._dragManager.getX();
      this._dragY = this._dragManager.getY();
      let motionUpdated = false;
      this._model.loadParameters();
      if (this._motionManager.isFinished()) {
        this.startRandomMotion(
          MotionGroupIdle,
          PriorityIdle
        );
      } else {
        motionUpdated = this._motionManager.updateMotion(
          this._model,
          deltaTimeSeconds
        );
      }
      this._model.saveParameters();
      if (!motionUpdated) {
        if (this._eyeBlink != null) {
          this._eyeBlink.updateParameters(this._model, deltaTimeSeconds);
        }
      }
      if (this._expressionManager != null) {
        this._expressionManager.updateMotion(this._model, deltaTimeSeconds);
      }
      if (Number.isFinite(this._externalEyeBlinkValue)) {
        const value = this._externalEyeBlinkValue;
        if (this._eyeBlinkIds.getSize() > 0) {
          for (let i = 0; i < this._eyeBlinkIds.getSize(); ++i) {
            this._model.setParameterValueById(this._eyeBlinkIds.at(i), value);
          }
        } else {
          const idManager = CubismFramework.getIdManager();
          if (idManager) {
            this._model.setParameterValueById(
              idManager.getId(CubismDefaultParameterId.ParamEyeLOpen),
              value
            );
            this._model.setParameterValueById(
              idManager.getId(CubismDefaultParameterId.ParamEyeROpen),
              value
            );
          }
        }
      }
      this._model.addParameterValueById(this._idParamAngleX, this._dragX * 30);
      this._model.addParameterValueById(this._idParamAngleY, this._dragY * 30);
      this._model.addParameterValueById(
        this._idParamAngleZ,
        this._dragX * this._dragY * -30
      );
      this._model.addParameterValueById(
        this._idParamBodyAngleX,
        this._dragX * 10
      );
      this._model.addParameterValueById(this._idParamEyeBallX, this._dragX);
      this._model.addParameterValueById(this._idParamEyeBallY, this._dragY);
      if (this._breath != null) {
        this._breath.updateParameters(this._model, deltaTimeSeconds);
      }
      if (this._physics != null) {
        this._physics.evaluate(this._model, deltaTimeSeconds);
      }
      if (this._lipsync) {
        let value = 0;
        this._wavFileHandler.update(deltaTimeSeconds);
        value = this._wavFileHandler.getRms();
        value = Math.min(1, value * 1.5);
        if (Number.isFinite(this._externalLipSyncValue)) {
          value = this._externalLipSyncValue;
        }
        const lipSyncWeight = Number.isFinite(this._externalLipSyncValue) ? 1 : 4;
        for (let i = 0; i < this._lipSyncIds.getSize(); ++i) {
          this._model.addParameterValueById(
            this._lipSyncIds.at(i),
            value,
            lipSyncWeight
          );
        }
      }
      if (this._pose != null) {
        this._pose.updateParameters(this._model, deltaTimeSeconds);
      }
      this._model.update();
    }
    setExternalLipSyncValue(value) {
      const next = Number(value);
      this._externalLipSyncValue = Number.isFinite(next) ? Math.max(0, Math.min(1, next)) : null;
    }
    setExternalEyeBlinkValue(value) {
      const next = Number(value);
      this._externalEyeBlinkValue = Number.isFinite(next) ? Math.max(0, Math.min(1, next)) : null;
    }
    /**
     * 引数で指定したモーションの再生を開始する
     * @param group モーショングループ名
     * @param no グループ内の番号
     * @param priority 優先度
     * @param onFinishedMotionHandler モーション再生終了時に呼び出されるコールバック関数
     * @return 開始したモーションの識別番号を返す。個別のモーションが終了したか否かを判定するisFinished()の引数で使用する。開始できない時は[-1]
     */
    startMotion(group, no, priority, onFinishedMotionHandler) {
      if (priority === 3 && DebugLogEnable) {
        console.log(`[APP] startMotion: Attempting to start tap motion. Group: '${group}', Index: ${no}`);
      }
      if (priority == PriorityForce) {
        this._motionManager.setReservePriority(priority);
      } else if (!this._motionManager.reserveMotion(priority)) {
        if (this._debugMode) {
          LAppPal.printMessage("[APP]can't start motion.");
        }
        return InvalidMotionQueueEntryHandleValue;
      }
      const motionFileName = this._modelSetting.getMotionFileName(group, no);
      const name = `${group}_${no}`;
      let motion = this._motions.getValue(name);
      let autoDelete = false;
      if (motion == null) {
        if (DebugLogEnable) {
          console.log(`[APP] startMotion: Motion '${name}' not found in cache, fetching: ${motionFileName}`);
        }
        fetch(`${this._modelHomeDir}${motionFileName}`).then((response) => {
          if (response.ok) {
            return response.arrayBuffer();
          } else if (response.status >= 400) {
            CubismLogError(
              `Failed to load file ${this._modelHomeDir}${motionFileName}`
            );
            return new ArrayBuffer(0);
          }
        }).then((arrayBuffer) => {
          motion = this.loadMotion(
            arrayBuffer,
            arrayBuffer.byteLength,
            null,
            // Pass null for name here? Original code did. Let's keep it for now.
            onFinishedMotionHandler
          );
          if (motion == null) {
            if (DebugLogEnable) {
              console.error(`[APP] startMotion: Failed to load motion from fetched data for '${name}'`);
            }
            return;
          }
          let fadeTime = this._modelSetting.getMotionFadeInTimeValue(
            group,
            no
          );
          if (fadeTime >= 0) {
            motion.setFadeInTime(fadeTime);
          }
          fadeTime = this._modelSetting.getMotionFadeOutTimeValue(group, no);
          if (fadeTime >= 0) {
            motion.setFadeOutTime(fadeTime);
          }
          motion.setEffectIds(this._eyeBlinkIds, this._lipSyncIds);
          autoDelete = true;
          if (DebugLogEnable) {
            console.log(`[APP] startMotion: Starting fetched motion '${name}'`);
          }
          this._motionManager.startMotionPriority(
            motion,
            autoDelete,
            priority
          );
        });
        return InvalidMotionQueueEntryHandleValue;
      } else {
        if (DebugLogEnable) {
          console.log(`[APP] startMotion: Motion '${name}' found in cache. Starting.`);
        }
        motion.setFinishedMotionHandler(onFinishedMotionHandler);
        return this._motionManager.startMotionPriority(
          motion,
          autoDelete,
          // Should be false for cached motions? Let's assume true based on original code.
          priority
        );
      }
    }
    /**
     * ランダムに選ばれたモーションの再生を開始する。
     * @param group モーショングループ名
     * @param priority 優先度
     * @param onFinishedMotionHandler モーション再生終了時に呼び出されるコールバック関数
     * @return 開始したモーションの識別番号を返す。個別のモーションが終了したか否かを判定するisFinished()の引数で使用する。開始できない時は[-1]
     */
    startRandomMotion(group, priority, onFinishedMotionHandler) {
      if (DebugLogEnable) {
        console.log(`[APP] startRandomMotion called. Group: '${group}', Priority: ${priority}`);
      }
      if (this._modelSetting.getMotionCount(group) == 0) {
        if (DebugLogEnable) {
          console.warn(`[APP] startRandomMotion: No motions found in group '${group}'`);
        }
        return InvalidMotionQueueEntryHandleValue;
      }
      const no = Math.floor(
        Math.random() * this._modelSetting.getMotionCount(group)
      );
      if (DebugLogEnable) {
        console.log(`[APP] startRandomMotion: Selected random index ${no} from group '${group}'`);
      }
      return this.startMotion(group, no, priority, onFinishedMotionHandler);
    }
    /**
     * 引数で指定した表情モーションをセットする
     *
     * @param expressionId 表情モーションのID
     */
    setExpression(expressionId) {
      const motion = this._expressions.getValue(expressionId);
      if (this._debugMode) {
        LAppPal.printMessage(`[APP]expression: [${expressionId}]`);
      }
      if (motion != null) {
        this._expressionManager.startMotionPriority(
          motion,
          false,
          PriorityForce
        );
      } else {
        if (this._debugMode) {
          LAppPal.printMessage(`[APP]expression[${expressionId}] is null`);
        }
      }
    }
    /**
     * ランダムに選ばれた表情モーションをセットする
     */
    setRandomExpression() {
      if (this._expressions.getSize() == 0) {
        return;
      }
      const no = Math.floor(Math.random() * this._expressions.getSize());
      for (let i = 0; i < this._expressions.getSize(); i++) {
        if (i == no) {
          const name = this._expressions._keyValues[i].first;
          this.setExpression(name);
          return;
        }
      }
    }
    /**
     * イベントの発火を受け取る
     */
    motionEventFired(eventValue) {
      CubismLogInfo("{0} is fired on LAppModel!!", eventValue.s);
    }
    /**
     * 当たり判定テスト
     * 指定ＩＤの頂点リストから矩形を計算し、座標をが矩形範囲内か判定する。
     *
     * @param hitArenaName  当たり判定をテストする対象のID
     * @param x             判定を行うX座標
     * @param y             判定を行うY座標
     */
    hitTest(hitArenaName, x, y) {
      if (this._opacity < 1) {
        return false;
      }
      const count = this._modelSetting.getHitAreasCount();
      for (let i = 0; i < count; i++) {
        if (this._modelSetting.getHitAreaName(i) == hitArenaName) {
          const drawId = this._modelSetting.getHitAreaId(i);
          return this.isHit(drawId, x, y);
        }
      }
      return false;
    }
    /**
     * Test if a point hits any part of the model's defined hit areas.
     * @param x X coordinate to test
     * @param y Y coordinate to test
     * @returns The name of the hit area if hit, otherwise null.
     */
    anyhitTest(x, y) {
      var _a;
      if (this._opacity < 1) {
        return null;
      }
      const count = this._modelSetting.getHitAreasCount();
      for (let i = 0; i < count; i++) {
        const drawId = this._modelSetting.getHitAreaId(i);
        const hit = this.isHit(drawId, x, y);
        if (hit) {
          const hitAreaIdHandle = this._modelSetting.getHitAreaId(i);
          const idString = (_a = hitAreaIdHandle == null ? void 0 : hitAreaIdHandle._id) == null ? void 0 : _a.s;
          if (DebugLogEnable) {
            console.log(`[APP] anyhitTest: Hit detected. ID Handle:`, hitAreaIdHandle, ` Extracted ID String: ${idString}`);
          }
          return idString || null;
        }
      }
      if (DebugLogEnable) {
      }
      return null;
    }
    /**
     * Load motions for the model
     * @param group Motion group name
     */
    preLoadMotionGroup(group) {
      for (let i = 0; i < this._modelSetting.getMotionCount(group); i++) {
        const motionFileName = this._modelSetting.getMotionFileName(group, i);
        const name = `${group}_${i}`;
        if (this._debugMode) {
          LAppPal.printMessage(
            `[APP]load motion: ${motionFileName} => [${name}]`
          );
        }
        fetch(`${this._modelHomeDir}${motionFileName}`).then((response) => {
          if (response.ok) {
            return response.arrayBuffer();
          } else if (response.status >= 400) {
            CubismLogError(
              `Failed to load file ${this._modelHomeDir}${motionFileName}`
            );
            return null;
          }
        }).then((arrayBuffer) => {
          if (!arrayBuffer) {
            this._allMotionCount--;
            return;
          }
          const tmpMotion = this.loadMotion(
            arrayBuffer,
            arrayBuffer.byteLength,
            name
          );
          if (tmpMotion != null) {
            let fadeTime = this._modelSetting.getMotionFadeInTimeValue(
              group,
              i
            );
            if (fadeTime >= 0) {
              tmpMotion.setFadeInTime(fadeTime);
            }
            fadeTime = this._modelSetting.getMotionFadeOutTimeValue(group, i);
            if (fadeTime >= 0) {
              tmpMotion.setFadeOutTime(fadeTime);
            }
            tmpMotion.setEffectIds(this._eyeBlinkIds, this._lipSyncIds);
            if (this._motions.getValue(name) != null) {
              ACubismMotion.delete(this._motions.getValue(name));
            }
            this._motions.setValue(name, tmpMotion);
            this._motionCount++;
            if (this._motionCount >= this._allMotionCount) {
              this._state = 20 /* LoadTexture */;
              this._motionManager.stopAllMotions();
              this._updating = false;
              this._initialized = true;
              this.createRenderer();
              this.setupTextures();
              this.getRenderer().startUp(gl);
            }
          } else {
            this._allMotionCount--;
          }
        }).catch((error) => {
          CubismLogError(`Failed to load motion: ${error}`);
          this._allMotionCount--;
        });
      }
    }
    /**
     * すべてのモーションデータを解放する。
     */
    releaseMotions() {
      this._motions.clear();
    }
    /**
     * 全ての表情データを解放する。
     */
    releaseExpressions() {
      this._expressions.clear();
    }
    /**
     * モデルを描画する処理。モデルを描画する空間のView-Projection行列を渡す。
     */
    doDraw() {
      if (this._model == null) return;
      const viewport = [0, 0, canvas.width, canvas.height];
      this.getRenderer().setRenderState(frameBuffer, viewport);
      this.getRenderer().drawModel();
    }
    /**
     * モデルを描画する処理。モデルを描画する空間のView-Projection行列を渡す。
     */
    draw(matrix) {
      if (this._model == null) {
        return;
      }
      if (this._state == 22 /* CompleteSetup */) {
        matrix.multiplyByMatrix(this._modelMatrix);
        this.getRenderer().setMvpMatrix(matrix);
        this.doDraw();
      }
    }
    async hasMocConsistencyFromFile() {
      CSM_ASSERT(this._modelSetting.getModelFileName().localeCompare(``));
      if (this._modelSetting.getModelFileName() != "") {
        const modelFileName = this._modelSetting.getModelFileName();
        const response = await fetch(`${this._modelHomeDir}${modelFileName}`);
        const arrayBuffer = await response.arrayBuffer();
        this._consistency = CubismMoc.hasMocConsistency(arrayBuffer);
        if (!this._consistency) {
          CubismLogInfo("Inconsistent MOC3.");
        } else {
          CubismLogInfo("Consistent MOC3.");
        }
        return this._consistency;
      } else {
        LAppPal.printMessage("Model data does not exist.");
      }
    }
    /**
     * Test if a point hits the model's rendered area
     * This is a fallback method when no hit areas are defined
     * @param x X coordinate to test
     * @param y Y coordinate to test
     */
    isHitOnModel(x, y) {
      if (this._opacity < 1) {
        return false;
      }
      const drawableCount = this._model.getDrawableCount();
      const matrix = this._modelMatrix.getArray();
      const det = matrix[0] * matrix[5] - matrix[1] * matrix[4];
      if (Math.abs(det) < 1e-4) {
        return false;
      }
      const invDet = 1 / det;
      const invMatrix = {
        a: matrix[5] * invDet,
        b: -matrix[1] * invDet,
        c: -matrix[4] * invDet,
        d: matrix[0] * invDet,
        tx: (matrix[4] * matrix[13] - matrix[5] * matrix[12]) * invDet,
        ty: (matrix[1] * matrix[12] - matrix[0] * matrix[13]) * invDet
      };
      const transformedPoint = {
        x: x * invMatrix.a + y * invMatrix.c + invMatrix.tx,
        y: x * invMatrix.b + y * invMatrix.d + invMatrix.ty
      };
      for (let i = 0; i < drawableCount; i++) {
        if (!this._model.getDrawableDynamicFlagIsVisible(i)) {
          continue;
        }
        const vertices = this._model.getDrawableVertices(i);
        let minX = vertices[0];
        let minY = vertices[1];
        let maxX = vertices[0];
        let maxY = vertices[1];
        for (let j = 2; j < vertices.length; j += 2) {
          const vx = vertices[j];
          const vy = vertices[j + 1];
          minX = Math.min(minX, vx);
          minY = Math.min(minY, vy);
          maxX = Math.max(maxX, vx);
          maxY = Math.max(maxY, vy);
        }
        if (transformedPoint.x >= minX && transformedPoint.x <= maxX && transformedPoint.y >= minY && transformedPoint.y <= maxY) {
          return true;
        }
      }
      return false;
    }
    /**
     * Performs a hit test with fallback if the first one fails.
     * 
     * @param x - X coordinate to test
     * @param y - Y coordinate to test
     * @returns boolean indicating if any hit was detected
     */
    anyHitTestWithFallback(x, y) {
      const hitAreaName = this.anyhitTest(x, y);
      return hitAreaName !== null || this.isHitOnModel(x, y);
    }
    /**
     * Starts a tap motion based on the hit area and configuration.
     * @param hitAreaName The name of the hit area that was tapped, or null if no specific area was hit
     * @param tapMotionsConfig The tap motion configuration from modelInfo
     */
    startTapMotion(hitAreaName, tapMotionsConfig) {
      if (DebugLogEnable) {
        console.log(`[APP] startTapMotion called. Hit area: ${hitAreaName}`);
      }
      if (!tapMotionsConfig || Object.keys(tapMotionsConfig).length === 0) {
        if (DebugLogEnable) {
          console.log("[APP] No tap motions configured.");
        }
        return;
      }
      let motionsToConsider = {};
      let areaSpecificHit = false;
      if (hitAreaName && tapMotionsConfig[hitAreaName]) {
        motionsToConsider = tapMotionsConfig[hitAreaName];
        areaSpecificHit = true;
        if (DebugLogEnable) {
          console.log(`[APP] startTapMotion: Using motions for specific area: ${hitAreaName}`, motionsToConsider);
        }
      }
      if (!areaSpecificHit) {
        motionsToConsider = {};
        Object.values(tapMotionsConfig).forEach((areaMotions) => {
          for (const [motionName, weight] of Object.entries(areaMotions)) {
            if (motionsToConsider[motionName]) {
              motionsToConsider[motionName] += Number(weight);
            } else {
              motionsToConsider[motionName] = Number(weight);
            }
          }
        });
        if (DebugLogEnable) {
          console.log("[APP] startTapMotion: Using combined motions:", motionsToConsider);
        }
      }
      if (Object.keys(motionsToConsider).length === 0) {
        if (DebugLogEnable) {
          console.log("[APP] startTapMotion: No motions found to consider.");
        }
        return;
      }
      const motionGroups = Object.keys(motionsToConsider);
      const weights = Object.values(motionsToConsider).map(Number);
      const totalWeight = weights.reduce((sum, w) => sum + (isNaN(w) ? 0 : w), 0);
      if (DebugLogEnable) {
        console.log(`[APP] startTapMotion: Motion groups: ${motionGroups}, Weights: ${weights}, Total weight: ${totalWeight}`);
      }
      if (totalWeight <= 0) {
        if (DebugLogEnable) {
          console.log("[APP] startTapMotion: Total weight is zero or invalid.");
        }
        return;
      }
      let random = Math.random() * totalWeight;
      let selectedGroupName = null;
      for (let i = 0; i < motionGroups.length; i++) {
        const weight = isNaN(weights[i]) ? 0 : weights[i];
        if (random < weight) {
          selectedGroupName = motionGroups[i];
          break;
        }
        random -= weight;
      }
      if (DebugLogEnable) {
        console.log(`[APP] startTapMotion: Selected group: ${selectedGroupName}`);
      }
      if (selectedGroupName !== null) {
        this.startRandomMotion(selectedGroupName, 3);
      } else {
        if (DebugLogEnable) {
          console.log("[APP] startTapMotion: Could not select a motion group.");
        }
      }
    }
    // MOC3一貫性チェック管理用
  };

  // .trellis/workspace/lapp-runtime-src/src/renderer/WebSDK/src/lapplive2dmanager.ts
  var s_instance5 = null;
  var LAppLive2DManager = class _LAppLive2DManager {
    /**
     * コンストラクタ
     */
    constructor() {
      __publicField(this, "_viewMatrix");
      // モデル描画に用いるview行列
      __publicField(this, "_models");
      // モデルインスタンスのコンテナ
      __publicField(this, "_sceneIndex");
      // 表示するシーンのインデックス値
      // モーション再生終了のコールバック関数
      __publicField(this, "_finishedMotion", (self) => {
        LAppPal.printMessage("Motion Finished:");
        console.log(self);
      });
      this._viewMatrix = new CubismMatrix44();
      this._models = new csmVector();
      this._sceneIndex = 0;
      this.changeScene(this._sceneIndex);
    }
    /**
     * クラスのインスタンス（シングルトン）を返す。
     * インスタンスが生成されていない場合は内部でインスタンスを生成する。
     * 
     * 返回类的实例（单例）。
     * 如果尚未创建实例，则在内部创建实例。
     *
     * @return クラスのインスタンス
     */
    static getInstance() {
      if (s_instance5 == null) {
        s_instance5 = new _LAppLive2DManager();
      }
      return s_instance5;
    }
    /**
     * クラスのインスタンス（シングルトン）を解放する。
     * 
     * 释放类的实例（单例）。
     */
    static releaseInstance() {
      if (s_instance5 != null) {
        s_instance5 = void 0;
      }
      s_instance5 = null;
    }
    /**
     * 現在のシーンで保持しているモデルを返す。
     *
     * @param no モデルリストのインデックス値
     * @return モデルのインスタンスを返す。インデックス値が範囲外の場合はNULLを返す。
     */
    getModel(no) {
      if (no < this._models.getSize()) {
        return this._models.at(no);
      }
      return null;
    }
    /**
     * 現在のシーンで保持しているすべてのモデルを解放する
     */
    releaseAllModel() {
      for (let i = 0; i < this._models.getSize(); i++) {
        this._models.at(i).release();
        this._models.set(i, null);
      }
      this._models.clear();
    }
    /**
     * 画面をドラッグした時の処理
     * 
     * 当拖动屏幕时的处理
     *
     * @param x 画面のX座標
     * @param y 画面のY座標
     */
    onDrag(x, y) {
      for (let i = 0; i < this._models.getSize(); i++) {
        const model = this.getModel(i);
        if (model) {
          model.setDragging(x, y);
        }
      }
    }
    /**
     * 画面をタップした時の処理
     *
     * @param x 画面のX座標
     * @param y 画面のY座標
     */
    onTap(x, y) {
      if (DebugLogEnable) {
        LAppPal.printMessage(
          `[APP]tap point: {x: ${x.toFixed(2)} y: ${y.toFixed(2)}}`
        );
      }
      for (let i = 0; i < this._models.getSize(); i++) {
        if (this._models.at(i).hitTest(HitAreaNameHead, x, y)) {
          if (DebugLogEnable) {
            LAppPal.printMessage(
              `[APP]hit area: [${HitAreaNameHead}]`
            );
          }
          this._models.at(i).setRandomExpression();
        } else if (this._models.at(i).hitTest(HitAreaNameBody, x, y)) {
          if (DebugLogEnable) {
            LAppPal.printMessage(
              `[APP]hit area: [${HitAreaNameBody}]`
            );
          }
          this._models.at(i).startRandomMotion(
            MotionGroupTapBody,
            PriorityNormal,
            this._finishedMotion
          );
        }
      }
    }
    /**
     * 画面を更新するときの処理
     * モデルの更新処理及び描画処理を行う
     */
    onUpdate() {
      const { width, height } = canvas;
      const modelCount = this._models.getSize();
      for (let i = 0; i < modelCount; ++i) {
        const projection = new CubismMatrix44();
        const model = this.getModel(i);
        if (model.getModel()) {
          if (model.getModel().getCanvasWidth() > 1 && width < height) {
            model.getModelMatrix().setWidth(2);
            projection.scale(1, width / height);
          } else {
            projection.scale(height / width, 1);
          }
          if (this._viewMatrix != null) {
            projection.multiplyByMatrix(this._viewMatrix);
          }
        }
        model.update();
        model.draw(projection);
      }
    }
    /**
     * 次のシーンに切りかえる
     * サンプルアプリケーションではモデルセットの切り替えを行う。
     */
    nextScene() {
      const no = (this._sceneIndex + 1) % ModelDirSize;
      this.changeScene(no);
    }
    /**
     * シーンを切り替える
     * サンプルアプリケーションではモデルセットの切り替えを行う。
     */
    changeScene(index) {
      this._sceneIndex = index;
      if (DebugLogEnable) {
        LAppPal.printMessage(`[APP]model index: ${this._sceneIndex}`);
      }
      const model = ModelDir[index];
      const modelPath = ResourcesPath + model + "/";
      let modelJsonName = ModelFileNames && ModelFileNames[index] ? ModelFileNames[index] : ModelDir[index];
      modelJsonName += ".model3.json";
      if (DebugLogEnable) {
        LAppPal.printMessage(`[APP]model path: ${modelPath}${modelJsonName}`);
      }
      this.releaseAllModel();
      this._models.pushBack(new LAppModel());
      this._models.at(0).loadAssets(modelPath, modelJsonName);
    }
    setViewMatrix(m) {
      for (let i = 0; i < 16; i++) {
        this._viewMatrix.getArray()[i] = m.getArray()[i];
      }
    }
  };

  // .trellis/workspace/lapp-runtime-src/src/renderer/WebSDK/src/lappadapter.ts
  var s_adapter_instance = null;
  var LAppAdapter = class _LAppAdapter {
    static getInstance() {
      if (s_adapter_instance == null) {
        s_adapter_instance = new _LAppAdapter();
      }
      return s_adapter_instance;
    }
    /* gets */
    getMgr() {
      return LAppLive2DManager.getInstance();
    }
    getModel() {
      return this.getMgr().getModel(0);
    }
    getIdManager() {
      return CubismFramework.getIdManager();
    }
    /* motion */
    getMotionGroups() {
      var _a, _b, _c;
      let groups = [];
      for (let i = 0; i < ((_a = this.getModel()) == null ? void 0 : _a._modelSetting.getMotionGroupCount()); i++) {
        groups.push((_c = (_b = this.getModel()) == null ? void 0 : _b._modelSetting.getMotionGroupName(i)) != null ? _c : "");
      }
      return groups;
    }
    getMotionCount(group) {
      var _a, _b;
      return (_b = (_a = this.getModel()) == null ? void 0 : _a._modelSetting.getMotionCount(group)) != null ? _b : 0;
    }
    startMotion(group, no, priority, onFinishedMotionHandler) {
      var _a, _b;
      return (_b = (_a = this.getModel()) == null ? void 0 : _a.startMotion(group, no, priority, onFinishedMotionHandler)) != null ? _b : InvalidMotionQueueEntryHandleValue;
    }
    /* expression */
    getExpressionCount() {
      var _a, _b;
      return (_b = (_a = this.getModel()) == null ? void 0 : _a._expressions.getSize()) != null ? _b : 0;
    }
    getExpressionName(index) {
      var _a, _b, _c;
      return (_c = (_b = (_a = this.getModel()) == null ? void 0 : _a._modelSetting) == null ? void 0 : _b.getExpressionName(index)) != null ? _c : "";
    }
    setExpression(name) {
      var _a;
      (_a = this.getModel()) == null ? void 0 : _a.setExpression(name);
    }
    setLipSyncValue(value) {
      var _a;
      (_a = this.getModel()) == null ? void 0 : _a.setExternalLipSyncValue(value);
    }
    setEyeBlinkValue(value) {
      var _a;
      (_a = this.getModel()) == null ? void 0 : _a.setExternalEyeBlinkValue(value);
    }
    // @deprecated
    nextChara() {
      this.getMgr().nextScene();
    }
    setChara(ModelDir2, ModelName) {
      var _a;
      const modelPath = (ModelDir2.endsWith("/") ? ModelDir2 : ModelDir2 + "/") + ModelName + "/";
      const modelJsonName = ModelName + ".model3.json";
      if (DebugLogEnable) {
        LAppPal.printMessage(`[APP]model Dir: ${modelPath}`);
      }
      this.getMgr().releaseAllModel();
      this.getMgr()._models.pushBack(new LAppModel());
      (_a = this.getMgr()._models.at(0)) == null ? void 0 : _a.loadAssets(modelPath, modelJsonName);
    }
    /* model position manipulation */
    getModelPosition() {
      const model = this.getModel();
      if (model && model._modelMatrix) {
        const matrix = model._modelMatrix.getArray();
        return {
          x: matrix[12],
          y: matrix[13]
        };
      }
      return { x: 0, y: 0 };
    }
    setModelPosition(x, y) {
      const model = this.getModel();
      if (model && model._modelMatrix) {
        const matrix = model._modelMatrix.getArray();
        const newMatrix = [...matrix];
        newMatrix[12] = x;
        newMatrix[13] = y;
        model._modelMatrix.setMatrix(newMatrix);
      }
    }
    // private _live2DMgr: LAppLive2DManager;
  };

  // .trellis/workspace/lapp-runtime-src/rikka-lapp-entry.ts
  function normalizeUrl(url) {
    return new URL(url || "/live2d-models/rikka_mikazuki/rikka_mikazuki.model3.json", location.origin).href;
  }
  function parseModelUrl(url) {
    const normalized = normalizeUrl(url);
    const parsed = new URL(normalized);
    const pathname = parsed.pathname;
    const lastSlash = pathname.lastIndexOf("/");
    const fileName = pathname.slice(lastSlash + 1);
    const modelFileName = fileName.replace(/\.model3\.json$/i, "");
    const parentSlash = pathname.lastIndexOf("/", lastSlash - 1);
    const modelDir = pathname.slice(parentSlash + 1, lastSlash);
    const baseUrl = `${parsed.origin}${pathname.slice(0, parentSlash + 1)}`;
    return { baseUrl, modelDir, modelFileName };
  }
  function configureModel(modelInfo = {}) {
    const { baseUrl, modelDir, modelFileName } = parseModelUrl(modelInfo.url);
    const kScale = Number(modelInfo.kScale);
    updateModelConfig(baseUrl, modelDir, modelFileName, Number.isFinite(kScale) ? kScale : void 0);
  }
  function exposeGlobals() {
    window.LAppDelegate = LAppDelegate;
    window.LAppLive2DManager = LAppLive2DManager;
    window.getLive2DManager = () => LAppLive2DManager.getInstance();
    window.getLAppAdapter = () => LAppAdapter.getInstance();
  }
  function initialize(modelInfo = {}) {
    configureModel(modelInfo);
    exposeGlobals();
    LAppLive2DManager.releaseInstance();
    const glManager = LAppGlManager.getInstance();
    const delegate = LAppDelegate.getInstance();
    if (!glManager || !delegate.initialize()) return null;
    delegate.run();
    return LAppAdapter.getInstance();
  }
  function setModelInfo(modelInfo = {}) {
    configureModel(modelInfo);
    LAppLive2DManager.releaseInstance();
    return LAppAdapter.getInstance();
  }
  function getAdapter() {
    exposeGlobals();
    return LAppAdapter.getInstance();
  }
  function release() {
    LAppDelegate.releaseInstance();
  }
  return __toCommonJS(rikka_lapp_entry_exports);
})();
